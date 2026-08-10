"""Cap-aware causal child authorization for one exact V0-075 V2 root epoch.

The frozen V2 child authority computes the complete set of active children
reachable from every root row and then applies one all-or-none 19-row cap.
That remains the required no-operator control.  This additive successor uses
the *failed proof frontier* as a causal filter: it packs complete catalogues
only for unmaterialized successors named by frontier obligations, in frozen
obligation priority order, without opening an observer or reading a target.

The result is an acquisition authorization, not an execution or certificate.
Discovery intents are executable only by the existing observer-signed
controller; validation templates remain blocked until that controller freezes
their exact aggregate-support epoch.  No statistical value, hidden law,
planner result, or terminal classification is accepted from a caller.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import hashlib
from typing import Any, Mapping, NoReturn

from acfqp.phase3e_ids import (
    Phase3EIdentityError,
    canonical_json_bytes,
    loads_canonical_json,
    parse_content_id,
)
from acfqp import v075_batch_native_planning_backend_v2 as planning
from acfqp import v075_live_dynamic_acquisition_authority_v2 as dynamic
from acfqp import v075_live_incremental_model_authority_v2 as live_model
from acfqp import v075_public_graph_semantics_v1 as graph
from acfqp import v075_public_target_tape_namespace_v2 as namespace_v2
from acfqp import v075_registered_occurrence_worker_v1 as worker


SCHEMA_VERSION = "3.0.0"
PROPOSED_CONTRACT_VERSION = "1.61.0"
PROFILE_KEY = "v075_live_batched_causal_child_authority_v3"
MAX_CANONICAL_INPUT_BYTES = 64 * 1024 * 1024

SELECTION_RULE = (
    "FAILED_FRONTIER_OBLIGATION_PRIORITY_THEN_COMPLETE_CHILD_CATALOGUE_"
    "UNION_UNDER_FROZEN_CAPS"
)
NO_OPERATOR_CONTROL_PROFILE = dynamic.PROFILE_KEY

PRODUCTION_INTEGRATION_READY = False
OBSERVER_ACCESS_ALLOWED = False
KERNEL_ACCESS_ALLOWED = False
TARGET_ACCESS_ALLOWED = False
PLAN_CERTIFICATE_ISSUANCE_ALLOWED = False
INFEASIBILITY_CERTIFICATE_ISSUANCE_ALLOWED = False

DOMAIN_TAGS = {
    "profile": "acfqp:v075-live-batched-causal-child-profile:v3",
    "candidate": "acfqp:v075-live-batched-causal-child-candidate:v3",
    "discovery": "acfqp:v075-live-batched-causal-child-discovery:v3",
    "validation": "acfqp:v075-live-batched-causal-child-validation:v3",
    "authorization": (
        "acfqp:v075-live-batched-causal-child-authorization:v3"
    ),
    "verification": (
        "acfqp:v075-live-batched-causal-child-verification:v3"
    ),
}
if len(DOMAIN_TAGS) != len(set(DOMAIN_TAGS.values())):  # pragma: no cover
    raise RuntimeError("live batched causal child domains must be unique")

_V2_CHILD_SEMANTIC_DOMAINS = {
    "discovery": (
        "acfqp:v075-live-dynamic-child-discovery-intent:v2"
    ),
    "validation": (
        "acfqp:v075-live-dynamic-child-validation-template:v2"
    ),
}
if (
    dynamic.DOMAIN_TAGS.get("child_discovery_intent")
    != _V2_CHILD_SEMANTIC_DOMAINS["discovery"]
    or dynamic.DOMAIN_TAGS.get("child_validation_template")
    != _V2_CHILD_SEMANTIC_DOMAINS["validation"]
):  # pragma: no cover - import-time source/schema compatibility lock
    raise RuntimeError("V2 child semantic projection domains changed")


class V075LiveBatchedCausalChildV3InvariantViolation(ValueError):
    """The root epoch, frontier cone, complete catalogue, or cap changed."""


def _fail(message: str) -> NoReturn:
    raise V075LiveBatchedCausalChildV3InvariantViolation(message)


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise V075LiveBatchedCausalChildV3InvariantViolation(
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
        raise V075LiveBatchedCausalChildV3InvariantViolation(
            str(error)
        ) from error


def _v2_semantic_hash(role: str, payload: Mapping[str, Any]) -> str:
    try:
        return hashlib.sha256(
            _V2_CHILD_SEMANTIC_DOMAINS[role].encode("utf-8")
            + b"\x00"
            + canonical_json_bytes(dict(payload))
        ).hexdigest()
    except (KeyError, TypeError, ValueError) as error:
        raise V075LiveBatchedCausalChildV3InvariantViolation(
            str(error)
        ) from error


_PROFILE_ISSUER = object()
_CANDIDATE_ISSUER = object()
_DISCOVERY_ISSUER = object()
_VALIDATION_ISSUER = object()
_AUTHORIZATION_ISSUER = object()
_VERIFICATION_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075LiveBatchedCausalChildProfileV3:
    _issuer: object = field(repr=False, compare=False)
    cap_profile_id: str
    maximum_new_child_action_rows: int
    maximum_incremental_draws: int
    child_discovery_draws: int
    child_validation_draws: int
    selection_rule: str = SELECTION_RULE
    no_operator_control_profile: str = NO_OPERATOR_CONTROL_PROFILE
    _profile_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        caps = worker.V075WorkerCapProfileV1()
        if (
            self._issuer is not _PROFILE_ISSUER
            or self.cap_profile_id != caps.cap_profile_id
            or self.maximum_new_child_action_rows
            != caps.maximum_new_child_action_rows
            or self.maximum_incremental_draws
            != caps.maximum_incremental_draws_per_adaptive_arm
            or self.child_discovery_draws
            != caps.new_child_discovery_draws_per_row
            or self.child_validation_draws
            != caps.new_child_validation_draws_per_row
            or self.selection_rule != SELECTION_RULE
            or self.no_operator_control_profile != NO_OPERATOR_CONTROL_PROFILE
        ):
            _fail("live batched causal child profile changed")
        _cid(self.cap_profile_id, "live batched causal cap profile")
        object.__setattr__(self, "_profile_id", _hash("profile", self._payload()))

    @property
    def per_new_row_draws(self) -> int:
        return self.child_discovery_draws + self.child_validation_draws

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_live_batched_causal_child_profile.v3",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "cap_profile_id": self.cap_profile_id,
            "maximum_new_child_action_rows": (
                self.maximum_new_child_action_rows
            ),
            "maximum_incremental_draws": self.maximum_incremental_draws,
            "child_discovery_draws": self.child_discovery_draws,
            "child_validation_draws": self.child_validation_draws,
            "per_new_row_draws": self.per_new_row_draws,
            "selection_rule": self.selection_rule,
            "no_operator_control_profile": self.no_operator_control_profile,
            "complete_child_catalogue_required": True,
            "duplicate_child_rows_charged_once": True,
            "failed_frontier_successor_filter_required": True,
            "post_run_cap_adjustment_allowed": False,
        }

    @property
    def profile_id(self) -> str:
        return self._profile_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "operator_profile_id": self.profile_id}


def freeze_v075_live_batched_causal_child_profile_v3(
) -> V075LiveBatchedCausalChildProfileV3:
    caps = worker.V075WorkerCapProfileV1()
    return V075LiveBatchedCausalChildProfileV3(
        _PROFILE_ISSUER,
        caps.cap_profile_id,
        caps.maximum_new_child_action_rows,
        caps.maximum_incremental_draws_per_adaptive_arm,
        caps.new_child_discovery_draws_per_row,
        caps.new_child_validation_draws_per_row,
    )


@dataclass(frozen=True, slots=True)
class V075LiveBatchedCausalChildCandidateV3:
    _issuer: object = field(repr=False, compare=False)
    child: dynamic.V075LiveDynamicChildStateV2 = field(repr=False)
    source_obligation_row_ids: tuple[str, ...]
    source_obligation_priority: int
    candidate_rank: int
    row_binding_ids: tuple[str, ...]
    incremental_draw_count: int
    _candidate_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if (
            self._issuer is not _CANDIDATE_ISSUER
            or type(self.child) is not dynamic.V075LiveDynamicChildStateV2
            or type(self.source_obligation_row_ids) is not tuple
            or not self.source_obligation_row_ids
            or self.source_obligation_row_ids
            != tuple(sorted(set(self.source_obligation_row_ids)))
            or type(self.source_obligation_priority) is not int
            or self.source_obligation_priority < 0
            or type(self.candidate_rank) is not int
            or self.candidate_rank < 0
        ):
            _fail("live batched causal child candidate is malformed")
        for value in self.source_obligation_row_ids:
            _cid(value, "candidate source obligation row")
        expected_rows = tuple(
            item.row_binding_id for item in self.child.row_bindings
        )
        edge_rows = {
            item.parent_numerical_row_id for item in self.child.causal_edges
        }
        profile = freeze_v075_live_batched_causal_child_profile_v3()
        if (
            self.child.modeled_row_binding_ids
            or self.child.unresolved_row_binding_ids != expected_rows
            or self.row_binding_ids != expected_rows
            or not set(self.source_obligation_row_ids) <= edge_rows
            or self.incremental_draw_count
            != len(expected_rows) * profile.per_new_row_draws
        ):
            _fail("causal candidate is not one complete missing catalogue")
        object.__setattr__(
            self,
            "_candidate_id",
            _hash("candidate", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_live_batched_causal_child_candidate.v3",
            "schema_version": SCHEMA_VERSION,
            "child_binding_id": self.child.child_binding_id,
            "child_state_id": self.child.state.state_id,
            "catalogue_id": self.child.catalogue.catalogue_id,
            "source_obligation_row_ids": list(
                self.source_obligation_row_ids
            ),
            "source_obligation_priority": self.source_obligation_priority,
            "candidate_rank": self.candidate_rank,
            "row_binding_ids": list(self.row_binding_ids),
            "new_action_row_count": len(self.row_binding_ids),
            "incremental_draw_count": self.incremental_draw_count,
            "complete_child_catalogue": True,
            "all_rows_unmaterialized_at_source_epoch": True,
            "causal_edges_join_frontier_obligations": True,
        }

    @property
    def candidate_id(self) -> str:
        return self._candidate_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "child": self.child.to_document(),
            "candidate_id": self.candidate_id,
        }


@dataclass(frozen=True, slots=True)
class V075LiveBatchedCausalChildDiscoveryIntentV3:
    _issuer: object = field(repr=False, compare=False)
    source_model_epoch_id: str
    source_numerical_model_id: str
    source_proof_id: str
    source_frontier_id: str
    source_head_id: str
    occurrence_id: str
    target_tape_namespace_id: str
    context_id: str
    arm: worker.V075WorkerArmV1
    operator_profile_id: str
    candidate_id: str
    child_binding_id: str
    child_state_id: str
    catalogue_id: str
    source_obligation_row_ids: tuple[str, ...]
    row_binding: graph.V075ObservationRowBindingV1
    stream_identity: graph.V075TransitionStreamIdentityV1
    ordinal: int
    _intent_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value, label in (
            (self.source_model_epoch_id, "batched child intent epoch"),
            (
                self.source_numerical_model_id,
                "batched child intent numerical model",
            ),
            (self.source_proof_id, "batched child intent proof"),
            (self.source_frontier_id, "batched child intent frontier"),
            (self.source_head_id, "batched child intent head"),
            (self.occurrence_id, "batched child intent occurrence"),
            (
                self.target_tape_namespace_id,
                "batched child intent namespace",
            ),
            (self.context_id, "batched child intent context"),
            (self.operator_profile_id, "batched child intent profile"),
            (self.candidate_id, "batched child intent candidate"),
            (self.child_binding_id, "batched child intent binding"),
            (self.child_state_id, "batched child intent state"),
            (self.catalogue_id, "batched child intent catalogue"),
        ):
            _cid(value, label)
        if (
            self._issuer is not _DISCOVERY_ISSUER
            or type(self.arm) is not worker.V075WorkerArmV1
            or self.arm is worker.V075WorkerArmV1.MATCHED_DIRECT_GROUND
            or type(self.source_obligation_row_ids) is not tuple
            or not self.source_obligation_row_ids
            or self.source_obligation_row_ids
            != tuple(sorted(set(self.source_obligation_row_ids)))
            or type(self.row_binding)
            is not graph.V075ObservationRowBindingV1
            or type(self.stream_identity)
            is not graph.V075TransitionStreamIdentityV1
            or self.row_binding.context_id != self.context_id
            or self.row_binding.state_id != self.child_state_id
            or self.row_binding.catalogue_id != self.catalogue_id
            or self.stream_identity.row_binding != self.row_binding
            or self.stream_identity.arm != self.arm.value
            or self.stream_identity.target_tape_namespace_id
            != self.target_tape_namespace_id
            or self.stream_identity.lane
            is not graph.V075ObservationLaneV1.DISCOVERY
            or self.stream_identity.observer_epoch_index != 0
            or type(self.ordinal) is not int
            or self.ordinal < 0
        ):
            _fail("live batched causal discovery intent is malformed")
        object.__setattr__(
            self,
            "_intent_id",
            _v2_semantic_hash("discovery", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": dynamic.LIVE_DYNAMIC_CHILD_SEMANTIC_SCHEMA,
            "schema_version": dynamic.SCHEMA_VERSION,
            "profile_key": dynamic.PROFILE_KEY,
            "semantic_role": dynamic.LIVE_DYNAMIC_CHILD_SEMANTIC_ROLE,
            "stage": "CHILD_DISCOVERY",
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
            "accepted_draw_count": dynamic.CHILD_DISCOVERY_DRAWS,
            "accepted_draw_end": dynamic.CHILD_DISCOVERY_DRAWS,
            "accepted_draw_cap": dynamic.CHILD_DISCOVERY_DRAWS,
            "ordinal": self.ordinal,
            "observer_execution_ready": True,
            "base_child_acquisition_consumes_promotion_round": False,
            "official_execution_allowed": False,
        }

    @property
    def intent_id(self) -> str:
        return self._intent_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "row_binding": self.row_binding.to_document(),
            "stream_identity": self.stream_identity.to_document(),
            "intent_id": self.intent_id,
        }


@dataclass(frozen=True, slots=True)
class V075LiveBatchedCausalChildValidationTemplateV3:
    _issuer: object = field(repr=False, compare=False)
    discovery_intent: V075LiveBatchedCausalChildDiscoveryIntentV3 = field(
        repr=False
    )
    ordinal: int
    _template_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if (
            self._issuer is not _VALIDATION_ISSUER
            or type(self.discovery_intent)
            is not V075LiveBatchedCausalChildDiscoveryIntentV3
            or self.ordinal != self.discovery_intent.ordinal
        ):
            _fail("live batched causal validation template is malformed")
        object.__setattr__(
            self,
            "_template_id",
            _v2_semantic_hash("validation", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        discovery = self.discovery_intent
        return {
            "schema": dynamic.LIVE_DYNAMIC_CHILD_VALIDATION_TEMPLATE_SCHEMA,
            "schema_version": dynamic.SCHEMA_VERSION,
            "profile_key": dynamic.PROFILE_KEY,
            "semantic_role": dynamic.LIVE_DYNAMIC_CHILD_SEMANTIC_ROLE,
            "stage": "CHILD_VALIDATION",
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
            "row_binding_id": discovery.row_binding.row_binding_id,
            "dependency_discovery_intent_id": discovery.intent_id,
            "stream_id": None,
            "support_freeze_id": None,
            "accepted_draw_start": 1,
            "accepted_draw_count": dynamic.CHILD_VALIDATION_DRAWS,
            "accepted_draw_end": dynamic.CHILD_VALIDATION_DRAWS,
            "accepted_draw_cap": (
                dynamic.CHILD_VALIDATION_DRAWS
                + dynamic.MAXIMUM_PROMOTION_ROUNDS * dynamic.PROMOTION_DRAWS
            ),
            "ordinal": self.ordinal,
            "observer_execution_ready": False,
            "observer_signed_complete_support_required": True,
            "validation_stream_must_be_derived_from_support_freeze": True,
            "base_child_acquisition_consumes_promotion_round": False,
            "official_execution_allowed": False,
        }

    @property
    def template_id(self) -> str:
        return self._template_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "template_id": self.template_id}


class V075LiveBatchedCausalChildOutcomeV3(str, Enum):
    AUTHORIZED = "BATCHED_CAUSAL_CHILD_ACQUISITION_AUTHORIZED"
    NO_CAUSAL_FRONTIER_CHILD = "NO_CAUSAL_FRONTIER_CHILD"
    CAUSAL_CONE_CAP_EXHAUSTED = "CAUSAL_CONE_CAP_EXHAUSTED"


@dataclass(frozen=True, slots=True)
class _SelectionFactsV3:
    candidates: tuple[V075LiveBatchedCausalChildCandidateV3, ...]
    selected_candidate_ids: tuple[str, ...]
    selected_child_state_ids: tuple[str, ...]
    selected_row_binding_ids: tuple[str, ...]
    incremental_draw_count: int


def _ordered_obligations(
    frontier: planning.V075FailedProofFrontierV2,
) -> tuple[planning.V075FrontierObligationV2, ...]:
    return tuple(
        sorted(
            frontier.obligations,
            key=lambda item: (
                -item.interval_width_sum,
                -item.other_upper,
                item.row_id,
            ),
        )
    )


def _candidate_registry(
    closure: dynamic.V075LiveDynamicChildClosureV2,
    profile: V075LiveBatchedCausalChildProfileV3,
) -> tuple[V075LiveBatchedCausalChildCandidateV3, ...]:
    frontier = closure.source_epoch.proof.failed_frontier
    if (
        closure.status
        is not (
            dynamic.V075LiveDynamicChildClosureStatusV2
            .CHILD_ACTION_ROW_CAP_EXCEEDED
        )
        or frontier is None
    ):
        _fail("batched causal successor requires the V2 row-cap control")
    obligations = _ordered_obligations(frontier)
    priority = {item.row_id: index for index, item in enumerate(obligations)}
    causal_rows: dict[str, set[str]] = {}
    for obligation in obligations:
        for state_id in obligation.unmaterialized_successor_ids:
            causal_rows.setdefault(state_id, set()).add(obligation.row_id)
    child_by_state = {item.state.state_id: item for item in closure.child_states}
    if not set(causal_rows) <= set(child_by_state):
        _fail("failed frontier names a child absent from the exact V2 closure")
    specifications = tuple(
        sorted(
            (
                min(priority[row_id] for row_id in rows),
                state_id,
                child_by_state[state_id],
                tuple(sorted(rows)),
            )
            for state_id, rows in causal_rows.items()
        )
    )
    result = []
    for rank, (first_priority, _state_id, child, rows) in enumerate(
        specifications
    ):
        row_ids = tuple(item.row_binding_id for item in child.row_bindings)
        result.append(
            V075LiveBatchedCausalChildCandidateV3(
                _CANDIDATE_ISSUER,
                child,
                rows,
                first_priority,
                rank,
                row_ids,
                len(row_ids) * profile.per_new_row_draws,
            )
        )
    return tuple(result)


def _selection_facts(
    closure: dynamic.V075LiveDynamicChildClosureV2,
    profile: V075LiveBatchedCausalChildProfileV3,
) -> _SelectionFactsV3:
    candidates = _candidate_registry(closure, profile)
    selected = []
    row_ids: set[str] = set()
    child_ids = []
    for candidate in candidates:
        proposed = row_ids | set(candidate.row_binding_ids)
        draws = len(proposed) * profile.per_new_row_draws
        if (
            len(proposed) <= profile.maximum_new_child_action_rows
            and draws <= profile.maximum_incremental_draws
        ):
            selected.append(candidate.candidate_id)
            child_ids.append(candidate.child.state.state_id)
            row_ids = proposed
    return _SelectionFactsV3(
        candidates,
        tuple(selected),
        tuple(child_ids),
        tuple(sorted(row_ids)),
        len(row_ids) * profile.per_new_row_draws,
    )


def _bootstrap_stream(
    *,
    namespace: namespace_v2.V075PublicTargetTapeNamespaceV2,
    row_binding: graph.V075ObservationRowBindingV1,
    arm: worker.V075WorkerArmV1,
) -> graph.V075TransitionStreamIdentityV1:
    try:
        root = graph.derive_shared_support_epoch_v1(
            namespace=namespace,
            row_binding=row_binding,
            epoch_index=0,
            evidence=(),
        )
        chain = graph.freeze_shared_support_chain_v1(
            namespace=namespace,
            row_binding=row_binding,
            epochs=(root,),
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
        raise V075LiveBatchedCausalChildV3InvariantViolation(
            "batched causal child bootstrap stream derivation failed"
        ) from error


@dataclass(frozen=True, slots=True)
class V075LiveBatchedCausalChildAuthorizationV3:
    _issuer: object = field(repr=False, compare=False)
    source_closure: dynamic.V075LiveDynamicChildClosureV2 = field(repr=False)
    profile: V075LiveBatchedCausalChildProfileV3
    candidates: tuple[V075LiveBatchedCausalChildCandidateV3, ...]
    outcome: V075LiveBatchedCausalChildOutcomeV3
    selected_candidate_ids: tuple[str, ...]
    selected_child_state_ids: tuple[str, ...]
    selected_row_binding_ids: tuple[str, ...]
    discovery_intents: tuple[
        V075LiveBatchedCausalChildDiscoveryIntentV3, ...
    ]
    validation_templates: tuple[
        V075LiveBatchedCausalChildValidationTemplateV3, ...
    ]
    incremental_draw_count: int
    _authorization_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if (
            self._issuer is not _AUTHORIZATION_ISSUER
            or type(self.source_closure)
            is not dynamic.V075LiveDynamicChildClosureV2
            or type(self.profile) is not V075LiveBatchedCausalChildProfileV3
            or type(self.outcome) is not V075LiveBatchedCausalChildOutcomeV3
            or type(self.candidates) is not tuple
            or type(self.discovery_intents) is not tuple
            or type(self.validation_templates) is not tuple
        ):
            _fail("live batched causal authorization is malformed")
        expected = _selection_facts(self.source_closure, self.profile)
        if (
            self.candidates != expected.candidates
            or self.selected_candidate_ids != expected.selected_candidate_ids
            or self.selected_child_state_ids
            != expected.selected_child_state_ids
            or self.selected_row_binding_ids
            != expected.selected_row_binding_ids
            or self.incremental_draw_count != expected.incremental_draw_count
        ):
            _fail("live batched causal authorization differs from exact replay")
        authorized = self.outcome is V075LiveBatchedCausalChildOutcomeV3.AUTHORIZED
        expected_outcome = (
            V075LiveBatchedCausalChildOutcomeV3.AUTHORIZED
            if expected.selected_candidate_ids
            else (
                V075LiveBatchedCausalChildOutcomeV3.NO_CAUSAL_FRONTIER_CHILD
                if not expected.candidates
                else (
                    V075LiveBatchedCausalChildOutcomeV3
                    .CAUSAL_CONE_CAP_EXHAUSTED
                )
            )
        )
        if self.outcome is not expected_outcome or authorized != bool(
            self.selected_candidate_ids
        ):
            _fail("live batched causal authorization outcome changed")
        if not authorized:
            if self.discovery_intents or self.validation_templates:
                _fail("non-authorized batched causal result contains work")
        else:
            if (
                tuple(item.ordinal for item in self.discovery_intents)
                != tuple(range(len(self.discovery_intents)))
                or len(self.validation_templates) != len(self.discovery_intents)
                or tuple(item.ordinal for item in self.validation_templates)
                != tuple(range(len(self.validation_templates)))
                or tuple(
                    item.discovery_intent.intent_id
                    for item in self.validation_templates
                )
                != tuple(item.intent_id for item in self.discovery_intents)
                or tuple(
                    item.row_binding.row_binding_id
                    for item in self.discovery_intents
                )
                != self.selected_row_binding_ids
                or sum(
                    dynamic.CHILD_DISCOVERY_DRAWS
                    + dynamic.CHILD_VALIDATION_DRAWS
                    for _item in self.discovery_intents
                )
                != self.incremental_draw_count
                or any(
                    item.source_model_epoch_id
                    != self.source_closure.source_epoch.model_epoch_id
                    or item.source_proof_id
                    != self.source_closure.source_epoch.proof.proof_id
                    or item.source_frontier_id
                    != (
                        self.source_closure.source_epoch.proof
                        .failed_frontier.frontier_id  # type: ignore[union-attr]
                    )
                    or item.source_head_id
                    != self.source_closure.source_epoch.head_id
                    or item.operator_profile_id != self.profile.profile_id
                    for item in self.discovery_intents
                )
            ):
                _fail("batched causal intent registry differs from selection")
        object.__setattr__(
            self,
            "_authorization_id",
            _hash("authorization", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        epoch = self.source_closure.source_epoch
        frontier = epoch.proof.failed_frontier
        assert frontier is not None
        return {
            "schema": "acfqp.v075_live_batched_causal_child_authorization.v3",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "source_model_epoch_id": epoch.model_epoch_id,
            "source_numerical_model_id": epoch.model.model_id,
            "source_proof_id": epoch.proof.proof_id,
            "source_frontier_id": frontier.frontier_id,
            "source_head_id": epoch.head_id,
            "source_v2_child_closure_id": self.source_closure.closure_id,
            "source_v2_child_closure_status": self.source_closure.status.value,
            "operator_profile_id": self.profile.profile_id,
            "authorization_outcome": self.outcome.value,
            "candidate_ids": [item.candidate_id for item in self.candidates],
            "selected_candidate_ids": list(self.selected_candidate_ids),
            "selected_child_state_ids": list(self.selected_child_state_ids),
            "selected_row_binding_ids": list(self.selected_row_binding_ids),
            "discovery_intent_ids": [
                item.intent_id for item in self.discovery_intents
            ],
            "discovery_candidate_bindings": [
                {
                    "discovery_intent_id": item.intent_id,
                    "candidate_id": item.candidate_id,
                    "source_obligation_row_ids": list(
                        item.source_obligation_row_ids
                    ),
                }
                for item in self.discovery_intents
            ],
            "validation_template_ids": [
                item.template_id for item in self.validation_templates
            ],
            "selected_child_catalogue_count": len(
                self.selected_candidate_ids
            ),
            "selected_new_action_row_count": len(
                self.selected_row_binding_ids
            ),
            "incremental_draw_count": self.incremental_draw_count,
            "maximum_new_child_action_rows": (
                self.profile.maximum_new_child_action_rows
            ),
            "maximum_incremental_draws": (
                self.profile.maximum_incremental_draws
            ),
            "selection_rule": self.profile.selection_rule,
            "no_operator_control_retained": True,
            "all_root_support_descriptors_examined_by_control": True,
            "only_failed_frontier_successors_selected": True,
            "complete_selected_child_catalogues": True,
            "frozen_before_target_access": True,
            "observer_calls": 0,
            "kernel_calls": 0,
            "world_model_rows_written": 0,
            "production_integration_ready": PRODUCTION_INTEGRATION_READY,
            "plan_certificate": False,
            "infeasibility_certificate": False,
        }

    @property
    def authorization_id(self) -> str:
        return self._authorization_id

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "source_v2_child_closure": self.source_closure.to_document(),
            "operator_profile": self.profile.to_document(),
            "candidates": [item.to_document() for item in self.candidates],
            "discovery_intents": [
                item.to_document() for item in self.discovery_intents
            ],
            "validation_templates": [
                item.to_document() for item in self.validation_templates
            ],
            "authorization_id": self.authorization_id,
        }


def _validate_namespace(
    *,
    namespace: namespace_v2.V075PublicTargetTapeNamespaceV2,
    epoch: live_model.V075LiveIncrementalModelEpochV2,
) -> None:
    if (
        type(namespace) is not namespace_v2.V075PublicTargetTapeNamespaceV2
        or graph.validate_v075_public_graph_namespace_v2(namespace)
        is not namespace
        or namespace.target_tape_namespace_id
        != epoch.occurrence_identity.target_tape_namespace_id
        or epoch.occurrence_identity.context_id != epoch.context_id
        or epoch.occurrence_identity.arm is not epoch.arm
    ):
        _fail("batched causal namespace or occurrence was transplanted")


def _authorize_from_closure(
    *,
    closure: dynamic.V075LiveDynamicChildClosureV2,
    namespace: namespace_v2.V075PublicTargetTapeNamespaceV2,
) -> V075LiveBatchedCausalChildAuthorizationV3:
    epoch = closure.source_epoch
    _validate_namespace(namespace=namespace, epoch=epoch)
    profile = freeze_v075_live_batched_causal_child_profile_v3()
    facts = _selection_facts(closure, profile)
    outcome = (
        V075LiveBatchedCausalChildOutcomeV3.AUTHORIZED
        if facts.selected_candidate_ids
        else (
            V075LiveBatchedCausalChildOutcomeV3.NO_CAUSAL_FRONTIER_CHILD
            if not facts.candidates
            else V075LiveBatchedCausalChildOutcomeV3.CAUSAL_CONE_CAP_EXHAUSTED
        )
    )
    candidate_by_id = {item.candidate_id: item for item in facts.candidates}
    selected = tuple(candidate_by_id[item] for item in facts.selected_candidate_ids)
    row_owners: dict[str, V075LiveBatchedCausalChildCandidateV3] = {}
    row_bindings: dict[str, graph.V075ObservationRowBindingV1] = {}
    for candidate in selected:
        for row in candidate.child.row_bindings:
            prior = row_owners.setdefault(row.row_binding_id, candidate)
            if prior.candidate_id != candidate.candidate_id:
                _fail("one selected child row belongs to multiple catalogues")
            row_bindings[row.row_binding_id] = row
    if tuple(sorted(row_bindings)) != facts.selected_row_binding_ids:
        _fail("selected child row registry differs from exact union")
    frontier = epoch.proof.failed_frontier
    assert frontier is not None
    discoveries = tuple(
        V075LiveBatchedCausalChildDiscoveryIntentV3(
            _DISCOVERY_ISSUER,
            epoch.model_epoch_id,
            epoch.model.model_id,
            epoch.proof.proof_id,
            frontier.frontier_id,
            epoch.head_id,
            epoch.occurrence_identity.occurrence_id,
            namespace.target_tape_namespace_id,
            epoch.context_id,
            epoch.arm,
            profile.profile_id,
            row_owners[row_id].candidate_id,
            row_owners[row_id].child.child_binding_id,
            row_owners[row_id].child.state.state_id,
            row_owners[row_id].child.catalogue.catalogue_id,
            row_owners[row_id].source_obligation_row_ids,
            row_bindings[row_id],
            _bootstrap_stream(
                namespace=namespace,
                row_binding=row_bindings[row_id],
                arm=epoch.arm,
            ),
            ordinal,
        )
        for ordinal, row_id in enumerate(facts.selected_row_binding_ids)
    )
    validations = tuple(
        V075LiveBatchedCausalChildValidationTemplateV3(
            _VALIDATION_ISSUER,
            item,
            item.ordinal,
        )
        for item in discoveries
    )
    return V075LiveBatchedCausalChildAuthorizationV3(
        _AUTHORIZATION_ISSUER,
        closure,
        profile,
        facts.candidates,
        outcome,
        facts.selected_candidate_ids,
        facts.selected_child_state_ids,
        facts.selected_row_binding_ids,
        discoveries,
        validations,
        facts.incremental_draw_count,
    )


def authorize_v075_live_batched_causal_children_v3(
    *,
    source_epoch: live_model.V075LiveIncrementalModelEpochV2,
    namespace: namespace_v2.V075PublicTargetTapeNamespaceV2,
) -> V075LiveBatchedCausalChildAuthorizationV3:
    """Freeze a complete-catalogue union without observer or target access."""

    closure = dynamic.freeze_v075_live_dynamic_child_closure_v2(
        source_epoch=source_epoch,
        namespace=namespace,
    )
    return _authorize_from_closure(closure=closure, namespace=namespace)


@dataclass(frozen=True, slots=True)
class V075LiveBatchedCausalChildVerificationV3:
    _issuer: object = field(repr=False, compare=False)
    authorization_id: str
    source_model_epoch_id: str
    source_frontier_id: str
    source_v2_child_closure_id: str
    selected_candidate_ids: tuple[str, ...]
    selected_row_binding_ids: tuple[str, ...]
    incremental_draw_count: int
    _verification_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value, label in (
            (self.authorization_id, "batched causal verification authorization"),
            (self.source_model_epoch_id, "batched causal verification epoch"),
            (self.source_frontier_id, "batched causal verification frontier"),
            (
                self.source_v2_child_closure_id,
                "batched causal verification V2 closure",
            ),
        ):
            _cid(value, label)
        if (
            self._issuer is not _VERIFICATION_ISSUER
            or type(self.selected_candidate_ids) is not tuple
            or type(self.selected_row_binding_ids) is not tuple
            or type(self.incremental_draw_count) is not int
            or self.incremental_draw_count < 0
        ):
            _fail("batched causal verification is malformed")
        object.__setattr__(
            self,
            "_verification_id",
            _hash("verification", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_live_batched_causal_child_verification.v3",
            "schema_version": SCHEMA_VERSION,
            "authorization_id": self.authorization_id,
            "source_model_epoch_id": self.source_model_epoch_id,
            "source_frontier_id": self.source_frontier_id,
            "source_v2_child_closure_id": self.source_v2_child_closure_id,
            "selected_candidate_ids": list(self.selected_candidate_ids),
            "selected_row_binding_ids": list(self.selected_row_binding_ids),
            "incremental_draw_count": self.incremental_draw_count,
            "exact_semantic_replay_complete": True,
            "observer_execution_performed": False,
            "target_access_performed": False,
            "plan_certificate": False,
        }

    @property
    def verification_id(self) -> str:
        return self._verification_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "verification_id": self.verification_id}


def verify_v075_live_batched_causal_child_authorization_bytes_v3(
    *,
    source_epoch: live_model.V075LiveIncrementalModelEpochV2,
    namespace: namespace_v2.V075PublicTargetTapeNamespaceV2,
    claimed_bytes: bytes,
) -> tuple[
    V075LiveBatchedCausalChildAuthorizationV3,
    V075LiveBatchedCausalChildVerificationV3,
]:
    """Recompute the exact V3 authorization and reject any byte drift."""

    if (
        type(claimed_bytes) is not bytes
        or not claimed_bytes
        or len(claimed_bytes) > MAX_CANONICAL_INPUT_BYTES
    ):
        _fail("batched causal authorization bytes are absent or over cap")
    try:
        claimed = loads_canonical_json(claimed_bytes)
    except (Phase3EIdentityError, TypeError, ValueError) as error:
        raise V075LiveBatchedCausalChildV3InvariantViolation(
            "batched causal authorization is not strict canonical JSON"
        ) from error
    if type(claimed) is not dict or canonical_json_bytes(claimed) != claimed_bytes:
        _fail("batched causal authorization is not one canonical object")
    exact = authorize_v075_live_batched_causal_children_v3(
        source_epoch=source_epoch,
        namespace=namespace,
    )
    if exact.canonical_bytes != claimed_bytes:
        _fail("claimed batched causal authorization differs from exact replay")
    frontier = exact.source_closure.source_epoch.proof.failed_frontier
    assert frontier is not None
    verification = V075LiveBatchedCausalChildVerificationV3(
        _VERIFICATION_ISSUER,
        exact.authorization_id,
        exact.source_closure.source_epoch.model_epoch_id,
        frontier.frontier_id,
        exact.source_closure.closure_id,
        exact.selected_candidate_ids,
        exact.selected_row_binding_ids,
        exact.incremental_draw_count,
    )
    return exact, verification


__all__ = (
    "NO_OPERATOR_CONTROL_PROFILE",
    "PROFILE_KEY",
    "PRODUCTION_INTEGRATION_READY",
    "SELECTION_RULE",
    "V075LiveBatchedCausalChildAuthorizationV3",
    "V075LiveBatchedCausalChildCandidateV3",
    "V075LiveBatchedCausalChildDiscoveryIntentV3",
    "V075LiveBatchedCausalChildOutcomeV3",
    "V075LiveBatchedCausalChildProfileV3",
    "V075LiveBatchedCausalChildV3InvariantViolation",
    "V075LiveBatchedCausalChildValidationTemplateV3",
    "V075LiveBatchedCausalChildVerificationV3",
    "authorize_v075_live_batched_causal_children_v3",
    "freeze_v075_live_batched_causal_child_profile_v3",
    "verify_v075_live_batched_causal_child_authorization_bytes_v3",
)
