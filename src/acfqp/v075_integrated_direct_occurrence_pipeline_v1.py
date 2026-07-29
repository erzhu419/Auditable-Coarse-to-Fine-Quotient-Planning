"""Matched-direct V0-075 occurrence pipeline before lifecycle closure.

The parent owns one fresh multistage observer lifecycle.  This component
freezes no private law and receives no kernel, random word, per-draw record,
or signing authority.  It performs only registered signed batch requests:

* every root action receives one DISCOVERY batch;
* every distinct nonfailure root successor observed in those signed batches
  contributes its complete legal-action catalogue;
* every resulting child row receives one DISCOVERY batch;
* all distinct projected states in every discovery row are frozen once;
* all rows advance together through the registered direct checkpoints.

Each checkpoint is compiled by the canonical batch-native backend and solved
by the exact matched-direct planner.  The first total-lift-ready checkpoint
stops acquisition.  Otherwise the occurrence returns a typed cap-exhausted
pre-close result after checkpoint 16,384.  A public verifier reconstructs the
complete closure, checkpoint history, work counters, and terminal result from
the signed aggregate batches without opening an observer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import hashlib
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes, parse_content_id
from acfqp import v075_batched_observer_authority_v1 as batched
from acfqp import v075_batch_native_statistical_backend_v1 as batch_backend
from acfqp import v075_learned_support_quotient_planners_v1 as planners
from acfqp import v075_multistage_observer_lifecycle_v1 as lifecycle
from acfqp import v075_public_campaign_authority_v1 as public_authority
from acfqp import v075_public_graph_semantics_v1 as graph
from acfqp import v075_registered_occurrence_worker_v1 as worker


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "1.40.0"
PROFILE_KEY = "v075_integrated_direct_occurrence_pipeline_v1"
PRODUCTION_INTEGRATION_READY = False
PER_DRAW_CAPABILITY_EXPANSION_ALLOWED = False

DOMAIN_TAGS = {
    "root_children": "acfqp:v075-direct-root-children:v1",
    "child_catalogue": "acfqp:v075-direct-child-catalogue:v1",
    "checkpoint": "acfqp:v075-direct-checkpoint-replay:v1",
    "counter": "acfqp:v075-direct-pipeline-counter:v1",
    "work": "acfqp:v075-direct-pipeline-work:v1",
    "result": "acfqp:v075-integrated-direct-preclose-result:v1",
    "verification": (
        "acfqp:v075-integrated-direct-preclose-verification:v1"
    ),
    "physical_cap_failure": (
        "acfqp:v075-integrated-direct-physical-row-cap-failure:v1"
    ),
}

if len(DOMAIN_TAGS) != len(set(DOMAIN_TAGS.values())):
    raise RuntimeError("V0-075 direct-pipeline domains must be unique")


class V075IntegratedDirectPipelineInvariantViolation(ValueError):
    """One direct occurrence or its public replay was invalid."""


class V075IntegratedDirectPhysicalRowCapExceeded(RuntimeError):
    """Typed noncertificate closure required by a physical-row cap."""

    def __init__(
        self,
        *,
        occurrence_id: str,
        observed_physical_rows: int,
        maximum_physical_rows: int,
        retained_root_batch_ids: tuple[str, ...],
    ) -> None:
        _cid(occurrence_id, "physical-row-cap occurrence")
        if (
            type(observed_physical_rows) is not int
            or type(maximum_physical_rows) is not int
            or observed_physical_rows <= maximum_physical_rows
            or maximum_physical_rows <= 0
            or type(retained_root_batch_ids) is not tuple
            or not retained_root_batch_ids
            or retained_root_batch_ids
            != tuple(sorted(set(retained_root_batch_ids)))
        ):
            _fail("physical-row-cap failure is malformed")
        for item in retained_root_batch_ids:
            _cid(item, "physical-row-cap retained root batch")
        self.occurrence_id = occurrence_id
        self.observed_physical_rows = observed_physical_rows
        self.maximum_physical_rows = maximum_physical_rows
        self.retained_root_batch_ids = retained_root_batch_ids
        super().__init__(
            "complete observed direct child closure exceeds the frozen "
            "physical-row cap"
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_integrated_direct_physical_row_cap_failure.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "occurrence_id": self.occurrence_id,
            "observed_physical_rows": self.observed_physical_rows,
            "maximum_physical_rows": self.maximum_physical_rows,
            "retained_root_batch_ids": list(
                self.retained_root_batch_ids
            ),
            "terminal_class": "ATTEMPT_CLOSURE_NONCERTIFICATE",
            "terminal_code": "DIRECT_PHYSICAL_ROW_CAP_EXHAUSTED",
            "lifecycle_close_required": True,
            "root_work_retained": True,
            "target_accessed": True,
            "scientific_plan_certificate": False,
        }

    @property
    def failure_id(self) -> str:
        return _hash("physical_cap_failure", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "failure_id": self.failure_id}


def _fail(message: str) -> None:
    raise V075IntegratedDirectPipelineInvariantViolation(message)


def _hash(role: str, payload: Mapping[str, Any]) -> str:
    try:
        return hashlib.sha256(
            DOMAIN_TAGS[role].encode("utf-8")
            + b"\x00"
            + canonical_json_bytes(dict(payload))
        ).hexdigest()
    except (KeyError, TypeError, ValueError) as error:
        raise V075IntegratedDirectPipelineInvariantViolation(
            str(error)
        ) from error


def _cid(value: Any, field_name: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise V075IntegratedDirectPipelineInvariantViolation(
            f"{field_name} must be one lowercase SHA-256 content ID"
        ) from error


class V075IntegratedDirectTerminalV1(str, Enum):
    READY_FOR_EXACT_TOTAL_LIFT = "READY_FOR_EXACT_TOTAL_LIFT"
    DIRECT_CHECKPOINT_CAP_EXHAUSTED = "DIRECT_CHECKPOINT_CAP_EXHAUSTED"


@dataclass(frozen=True, slots=True)
class V075DirectRootChildrenBindingV1:
    root_batch_id: str
    root_row_binding_id: str
    distinct_nonfailure_child_state_ids: tuple[str, ...]
    _binding_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        _cid(self.root_batch_id, "direct root discovery batch")
        _cid(self.root_row_binding_id, "direct root row binding")
        if (
            type(self.distinct_nonfailure_child_state_ids) is not tuple
            or self.distinct_nonfailure_child_state_ids
            != tuple(
                sorted(set(self.distinct_nonfailure_child_state_ids))
            )
        ):
            _fail("root-to-child state closure is duplicated or reordered")
        for item in self.distinct_nonfailure_child_state_ids:
            _cid(item, "direct observed child state")
        object.__setattr__(
            self,
            "_binding_id",
            _hash("root_children", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_direct_root_children_binding.v1",
            "schema_version": SCHEMA_VERSION,
            "root_batch_id": self.root_batch_id,
            "root_row_binding_id": self.root_row_binding_id,
            "distinct_nonfailure_child_state_ids": list(
                self.distinct_nonfailure_child_state_ids
            ),
            "all_distinct_nonfailure_outcomes_retained": True,
            "caller_selection_allowed": False,
        }

    @property
    def binding_id(self) -> str:
        return self._binding_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "binding_id": self.binding_id}


@dataclass(frozen=True, slots=True)
class V075DirectChildCatalogueBindingV1:
    state: graph.V075SymbolicGraphStateV1
    catalogue: graph.V075LegalActionCatalogueV1
    row_bindings: tuple[graph.V075ObservationRowBindingV1, ...]
    _binding_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if (
            type(self.state) is not graph.V075SymbolicGraphStateV1
            or type(self.catalogue) is not graph.V075LegalActionCatalogueV1
            or self.catalogue.state != self.state
            or self.catalogue.remaining_horizon != 1
            or self.state.failure
            or type(self.row_bindings) is not tuple
            or tuple(
                type(item) for item in self.row_bindings
            )
            != (graph.V075ObservationRowBindingV1,) * len(
                self.catalogue.actions
            )
            or tuple(item.action for item in self.row_bindings)
            != self.catalogue.actions
            or any(
                item.catalogue != self.catalogue
                for item in self.row_bindings
            )
        ):
            _fail("direct child catalogue is incomplete or transplanted")
        object.__setattr__(
            self,
            "_binding_id",
            _hash("child_catalogue", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_direct_child_catalogue_binding.v1",
            "schema_version": SCHEMA_VERSION,
            "child_state_id": self.state.state_id,
            "catalogue_id": self.catalogue.catalogue_id,
            "row_binding_ids": [
                item.row_binding_id for item in self.row_bindings
            ],
            "ground_actions": [
                list(item.action) for item in self.row_bindings
            ],
            "complete_legal_action_catalogue": True,
        }

    @property
    def binding_id(self) -> str:
        return self._binding_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "binding_id": self.binding_id}


@dataclass(frozen=True, slots=True)
class V075DirectCheckpointReplayV1:
    checkpoint: int
    request: batch_backend.V075BatchNativeBackendRequestV1
    backend_result: batch_backend.V075BatchNativeBackendResultV1
    planner_result: planners.V075SupportPlannerResultV1
    _checkpoint_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        checkpoints = worker.V075WorkerCapProfileV1().direct_validation_checkpoints
        if (
            type(self.checkpoint) is not int
            or self.checkpoint not in checkpoints
            or type(self.request)
            is not batch_backend.V075BatchNativeBackendRequestV1
            or self.request.arm
            is not worker.V075WorkerArmV1.MATCHED_DIRECT_GROUND
            or type(self.backend_result)
            is not batch_backend.V075BatchNativeBackendResultV1
            or self.backend_result.request != self.request
            or type(self.planner_result)
            is not planners.V075SupportPlannerResultV1
            or self.planner_result.graph.backend_result
            != self.backend_result.route_native_result
            or self.planner_result.route
            is not planners.V075PlannerRouteV1.MATCHED_DIRECT_GROUND
        ):
            _fail("direct checkpoint replay graph is malformed")
        validation_groups = tuple(
            values
            for values in self.request.batches_by_stream.values()
            if values[0].request.stream_identity.lane
            is graph.V075ObservationLaneV1.VALIDATION
        )
        if (
            not validation_groups
            or any(
                sum(
                    item.request.accepted_draw_count
                    for item in values
                )
                != self.checkpoint
                for values in validation_groups
            )
        ):
            _fail("direct checkpoint rows do not share one exact prefix")
        object.__setattr__(
            self,
            "_checkpoint_id",
            _hash("checkpoint", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_direct_checkpoint_replay.v1",
            "schema_version": SCHEMA_VERSION,
            "checkpoint": self.checkpoint,
            "request_id": self.request.request_id,
            "backend_result_id": self.backend_result.result_id,
            "backend_work_id": self.backend_result.work.work_id,
            "planner_result_id": self.planner_result.result_id,
            "planner_work_id": self.planner_result.work.work_id,
            "planner_status": self.planner_result.status.value,
            "ready_for_exact_total_lift": (
                self.planner_result.ready_for_exact_total_lift
            ),
            "batch_ids": [
                item.batch_id for item in self.request.batches
            ],
        }

    @property
    def checkpoint_id(self) -> str:
        return self._checkpoint_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "checkpoint_id": self.checkpoint_id}


DIRECT_PIPELINE_COUNTER_PATHS = (
    "common.pre_sampling_identity_checks",
    "common.open_lifecycle_checks",
    "common.signed_batches_retained",
    "common.per_draw_capabilities_materialized",
    "discovery.root_rows",
    "discovery.root_draws",
    "discovery.distinct_nonfailure_child_states",
    "discovery.child_catalogues",
    "discovery.child_rows",
    "discovery.child_draws",
    "support.rows_frozen",
    "support.distinct_states_frozen",
    "validation.rows",
    "validation.draws",
    "planning.checkpoints_evaluated",
    "planning.backend_compilations",
    "planning.matched_direct_planner_invocations",
    "planning.ready_checkpoint_count",
)


@dataclass(frozen=True, slots=True)
class V075IntegratedDirectCounterV1:
    path: str
    value: int
    observed: bool = True

    def __post_init__(self) -> None:
        if (
            self.path not in DIRECT_PIPELINE_COUNTER_PATHS
            or type(self.value) is not int
            or self.value < 0
            or self.observed is not True
        ):
            _fail("direct-pipeline counter is unknown or malformed")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_integrated_direct_counter.v1",
            "schema_version": SCHEMA_VERSION,
            "path": self.path,
            "value": self.value,
            "observed": True,
            "lane": "OPERATIONAL",
        }

    @property
    def counter_id(self) -> str:
        return _hash("counter", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "counter_id": self.counter_id}


@dataclass(frozen=True, slots=True)
class V075IntegratedDirectWorkV1:
    occurrence_id: str
    counters: tuple[V075IntegratedDirectCounterV1, ...]
    _work_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        _cid(self.occurrence_id, "direct-pipeline work occurrence")
        if (
            type(self.counters) is not tuple
            or tuple(item.path for item in self.counters)
            != DIRECT_PIPELINE_COUNTER_PATHS
            or any(
                type(item) is not V075IntegratedDirectCounterV1
                for item in self.counters
            )
            or self.values[
                "common.per_draw_capabilities_materialized"
            ]
            != 0
        ):
            _fail("direct-pipeline work is incomplete or reordered")
        object.__setattr__(
            self,
            "_work_id",
            _hash("work", self._payload()),
        )

    @property
    def values(self) -> dict[str, int]:
        return {item.path: item.value for item in self.counters}

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_integrated_direct_work.v1",
            "schema_version": SCHEMA_VERSION,
            "occurrence_id": self.occurrence_id,
            "counter_ids": [item.counter_id for item in self.counters],
            "required_counter_paths": list(DIRECT_PIPELINE_COUNTER_PATHS),
            "native_zeros_complete": True,
        }

    @property
    def work_id(self) -> str:
        return self._work_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "counters": [item.to_document() for item in self.counters],
            "work_id": self.work_id,
        }


_RESULT_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075IntegratedDirectOccurrenceResultV1:
    _issuer: object = field(repr=False, compare=False)
    occurrence_identity: (
        batch_backend.V075BatchNativeOccurrenceIdentityV1
    )
    open_binding: lifecycle.V075OpenMultistageLifecycleBindingV1
    batches: tuple[batched.V075SignedBatchedObservationV1, ...] = field(
        repr=False
    )
    events: tuple[lifecycle.V075MultistageLifecycleEventV1, ...]
    aggregate_support_evidence: tuple[
        graph.V075BatchAggregateSupportEvidenceV1, ...
    ]
    root_child_bindings: tuple[V075DirectRootChildrenBindingV1, ...]
    child_catalogue_bindings: tuple[
        V075DirectChildCatalogueBindingV1, ...
    ]
    checkpoint_history: tuple[V075DirectCheckpointReplayV1, ...]
    terminal: V075IntegratedDirectTerminalV1
    work: V075IntegratedDirectWorkV1
    _result_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if (
            self._issuer is not _RESULT_ISSUER
            or type(self.occurrence_identity)
            is not batch_backend.V075BatchNativeOccurrenceIdentityV1
            or self.occurrence_identity.arm
            is not worker.V075WorkerArmV1.MATCHED_DIRECT_GROUND
            or type(self.open_binding)
            is not lifecycle.V075OpenMultistageLifecycleBindingV1
            or self.open_binding.occurrence_id
            != self.occurrence_identity.occurrence_id
            or type(self.batches) is not tuple
            or not self.batches
            or any(
                type(item) is not batched.V075SignedBatchedObservationV1
                for item in self.batches
            )
            or type(self.events) is not tuple
            or not self.events
            or any(
                type(item) is not lifecycle.V075MultistageLifecycleEventV1
                for item in self.events
            )
            or type(self.aggregate_support_evidence) is not tuple
            or not self.aggregate_support_evidence
            or any(
                type(item)
                is not graph.V075BatchAggregateSupportEvidenceV1
                for item in self.aggregate_support_evidence
            )
            or type(self.root_child_bindings) is not tuple
            or not self.root_child_bindings
            or any(
                type(item) is not V075DirectRootChildrenBindingV1
                for item in self.root_child_bindings
            )
            or type(self.child_catalogue_bindings) is not tuple
            or any(
                type(item) is not V075DirectChildCatalogueBindingV1
                for item in self.child_catalogue_bindings
            )
            or type(self.checkpoint_history) is not tuple
            or not self.checkpoint_history
            or any(
                type(item) is not V075DirectCheckpointReplayV1
                for item in self.checkpoint_history
            )
            or type(self.terminal) is not V075IntegratedDirectTerminalV1
            or type(self.work) is not V075IntegratedDirectWorkV1
            or self.work.occurrence_id
            != self.occurrence_identity.occurrence_id
        ):
            _fail("integrated direct pre-close result is malformed")
        checkpoints = tuple(
            item.checkpoint for item in self.checkpoint_history
        )
        registered = (
            self.open_binding.route_cap_profile
            .direct_validation_checkpoints
        )
        if (
            checkpoints != registered[: len(checkpoints)]
            or any(
                item.request.occurrence_identity
                != self.occurrence_identity
                for item in self.checkpoint_history
            )
            or (
                self.terminal
                is V075IntegratedDirectTerminalV1
                .READY_FOR_EXACT_TOTAL_LIFT
            )
            != self.checkpoint_history[
                -1
            ].planner_result.ready_for_exact_total_lift
            or (
                self.terminal
                is V075IntegratedDirectTerminalV1
                .DIRECT_CHECKPOINT_CAP_EXHAUSTED
                and checkpoints[-1] != registered[-1]
            )
        ):
            _fail("direct terminal disagrees with its checkpoint history")
        object.__setattr__(
            self,
            "_result_id",
            _hash("result", self._payload()),
        )

    @property
    def final_backend_result(
        self,
    ) -> batch_backend.V075BatchNativeBackendResultV1:
        return self.checkpoint_history[-1].backend_result

    @property
    def final_planner_result(self) -> planners.V075SupportPlannerResultV1:
        return self.checkpoint_history[-1].planner_result

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_integrated_direct_occurrence_preclose_result.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "occurrence_id": self.occurrence_identity.occurrence_id,
            "pre_sampling_occurrence_identity_id": (
                self.occurrence_identity.occurrence_id
            ),
            "open_lifecycle_binding_id": self.open_binding.binding_id,
            "batch_ids_in_emission_order": [
                item.batch_id for item in self.batches
            ],
            "event_ids_in_causal_order": [
                item.event_id for item in self.events
            ],
            "aggregate_support_evidence_ids": [
                item.evidence_id
                for item in self.aggregate_support_evidence
            ],
            "root_child_binding_ids": [
                item.binding_id for item in self.root_child_bindings
            ],
            "child_catalogue_binding_ids": [
                item.binding_id for item in self.child_catalogue_bindings
            ],
            "checkpoint_ids": [
                item.checkpoint_id for item in self.checkpoint_history
            ],
            "terminal": self.terminal.value,
            "final_backend_result_id": (
                self.final_backend_result.result_id
            ),
            "final_planner_result_id": (
                self.final_planner_result.result_id
            ),
            "work_id": self.work.work_id,
            "lifecycle_closed": False,
            "ready_for_exact_total_lift": (
                self.final_planner_result.ready_for_exact_total_lift
            ),
            "complete_distinct_observed_child_closure": True,
            "per_draw_capability_count": 0,
            "law_or_kernel_access": False,
            "scientific_plan_certificate": False,
        }

    @property
    def result_id(self) -> str:
        return self._result_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "occurrence_identity": (
                self.occurrence_identity.to_document()
            ),
            "open_binding": self.open_binding.to_document(),
            "root_child_bindings": [
                item.to_document() for item in self.root_child_bindings
            ],
            "child_catalogue_bindings": [
                item.to_document()
                for item in self.child_catalogue_bindings
            ],
            "checkpoint_history": [
                item.to_document() for item in self.checkpoint_history
            ],
            "work": self.work.to_document(),
            "result_id": self.result_id,
        }

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())


def _context_from_binding(
    binding: lifecycle.V075OpenMultistageLifecycleBindingV1,
) -> public_authority.V075PublicReplicateContextV1:
    values = tuple(
        item
        for item in binding.namespace.family.replicate_contexts
        if item.context_id == binding.context_id
    )
    if len(values) != 1:
        _fail("open lifecycle context is not in its public namespace")
    return values[0]


def _bootstrap_stream(
    *,
    namespace: public_authority.V075PublicTargetTapeNamespaceV1,
    row_binding: graph.V075ObservationRowBindingV1,
) -> graph.V075TransitionStreamIdentityV1:
    root_epoch = graph.derive_shared_support_epoch_v1(
        namespace=namespace,
        row_binding=row_binding,
        epoch_index=0,
        evidence=(),
    )
    chain = graph.freeze_shared_support_chain_v1(
        namespace=namespace,
        row_binding=row_binding,
        epochs=(root_epoch,),
    )
    pairing = graph.freeze_five_arm_pairing_authority_v1(
        namespace=namespace,
        row_binding=row_binding,
        support_chain=chain,
    )
    return graph.derive_transition_stream_identity_v1(
        pairing_authority=pairing,
        arm=worker.V075WorkerArmV1.MATCHED_DIRECT_GROUND.value,
    )


def _states_by_outcome(
    *,
    context: public_authority.V075PublicReplicateContextV1,
    batch: batched.V075SignedBatchedObservationV1,
) -> dict[str, tuple[graph.V075SymbolicGraphStateV1, tuple[str, ...]]]:
    grouped: dict[
        str, tuple[graph.V075SymbolicGraphStateV1, list[str]]
    ] = {}
    for outcome in batch.outcomes:
        state = graph.V075SymbolicGraphStateV1(
            context,
            outcome.next_ranks,
            outcome.failure,
        )
        prior = grouped.get(state.state_id)
        if prior is None:
            grouped[state.state_id] = (state, [outcome.outcome_id])
        else:
            prior[1].append(outcome.outcome_id)
    return {
        state_id: (state, tuple(sorted(outcome_ids)))
        for state_id, (state, outcome_ids) in grouped.items()
    }


def _root_and_child_bindings(
    *,
    context: public_authority.V075PublicReplicateContextV1,
    root_batches: tuple[batched.V075SignedBatchedObservationV1, ...],
) -> tuple[
    tuple[V075DirectRootChildrenBindingV1, ...],
    tuple[V075DirectChildCatalogueBindingV1, ...],
]:
    roots = []
    child_by_id: dict[str, graph.V075SymbolicGraphStateV1] = {}
    for batch in root_batches:
        states = _states_by_outcome(context=context, batch=batch)
        children = []
        for state, _outcome_ids in states.values():
            corresponding = tuple(
                item
                for item in batch.outcomes
                if item.next_ranks == state.ranks
                and item.failure == state.failure
            )
            if any(not item.failure and item.terminal for item in corresponding):
                _fail("a root nonfailure outcome terminated before H=1")
            if not state.failure:
                children.append(state.state_id)
                child_by_id[state.state_id] = state
        roots.append(
            V075DirectRootChildrenBindingV1(
                batch.batch_id,
                batch.request.stream_identity.row_binding_id,
                tuple(sorted(children)),
            )
        )
    child_bindings = []
    for state_id in sorted(child_by_id):
        state = child_by_id[state_id]
        actions = graph.legal_action_triples_v1(
            context,
            state.ranks,
            state.failure,
        )
        if not actions:
            _fail("observed nonfailure child has no legal ground action")
        catalogue = graph.V075LegalActionCatalogueV1(
            context,
            state,
            1,
            actions,
        )
        child_bindings.append(
            V075DirectChildCatalogueBindingV1(
                state,
                catalogue,
                tuple(
                    graph.observation_row_binding_v1(
                        context,
                        catalogue,
                        action,
                    )
                    for action in catalogue.actions
                ),
            )
        )
    return tuple(roots), tuple(child_bindings)


def _canonical_support_outcome_ids(
    *,
    context: public_authority.V075PublicReplicateContextV1,
    batch: batched.V075SignedBatchedObservationV1,
) -> tuple[str, ...]:
    states = _states_by_outcome(context=context, batch=batch)
    return tuple(
        sorted(min(outcome_ids) for _state, outcome_ids in states.values())
    )


def _validation_stream(
    *,
    namespace: public_authority.V075PublicTargetTapeNamespaceV1,
    discovery_stream: graph.V075TransitionStreamIdentityV1,
    evidence: tuple[graph.V075BatchAggregateSupportEvidenceV1, ...],
) -> graph.V075TransitionStreamIdentityV1:
    root_epoch = discovery_stream.pairing_authority.support_chain.leaf
    validation_epoch = graph.derive_shared_support_epoch_v1(
        namespace=namespace,
        row_binding=discovery_stream.row_binding,
        epoch_index=1,
        evidence=evidence,
        parent=root_epoch,
    )
    chain = graph.freeze_shared_support_chain_v1(
        namespace=namespace,
        row_binding=discovery_stream.row_binding,
        epochs=(root_epoch, validation_epoch),
    )
    pairing = graph.freeze_five_arm_pairing_authority_v1(
        namespace=namespace,
        row_binding=discovery_stream.row_binding,
        support_chain=chain,
    )
    return graph.derive_transition_stream_identity_v1(
        pairing_authority=pairing,
        arm=worker.V075WorkerArmV1.MATCHED_DIRECT_GROUND.value,
    )


def _work(
    *,
    occurrence_id: str,
    root_batches: tuple[batched.V075SignedBatchedObservationV1, ...],
    child_bindings: tuple[V075DirectChildCatalogueBindingV1, ...],
    discovery_batches: tuple[
        batched.V075SignedBatchedObservationV1, ...
    ],
    evidence: tuple[graph.V075BatchAggregateSupportEvidenceV1, ...],
    final_batches: tuple[batched.V075SignedBatchedObservationV1, ...],
    history: tuple[V075DirectCheckpointReplayV1, ...],
) -> V075IntegratedDirectWorkV1:
    child_rows = sum(len(item.row_bindings) for item in child_bindings)
    validation = tuple(
        item
        for item in final_batches
        if item.request.stream_identity.lane
        is graph.V075ObservationLaneV1.VALIDATION
    )
    values = {
        "common.pre_sampling_identity_checks": 1,
        "common.open_lifecycle_checks": 1,
        "common.signed_batches_retained": len(final_batches),
        "common.per_draw_capabilities_materialized": 0,
        "discovery.root_rows": len(root_batches),
        "discovery.root_draws": sum(
            item.request.accepted_draw_count for item in root_batches
        ),
        "discovery.distinct_nonfailure_child_states": len(
            child_bindings
        ),
        "discovery.child_catalogues": len(child_bindings),
        "discovery.child_rows": child_rows,
        "discovery.child_draws": sum(
            item.request.accepted_draw_count
            for item in discovery_batches[len(root_batches) :]
        ),
        "support.rows_frozen": len(discovery_batches),
        "support.distinct_states_frozen": len(evidence),
        "validation.rows": len(discovery_batches),
        "validation.draws": sum(
            item.request.accepted_draw_count for item in validation
        ),
        "planning.checkpoints_evaluated": len(history),
        "planning.backend_compilations": len(history),
        "planning.matched_direct_planner_invocations": len(history),
        "planning.ready_checkpoint_count": int(
            history[-1].planner_result.ready_for_exact_total_lift
        ),
    }
    return V075IntegratedDirectWorkV1(
        occurrence_id,
        tuple(
            V075IntegratedDirectCounterV1(path, values[path])
            for path in DIRECT_PIPELINE_COUNTER_PATHS
        ),
    )


def _validate_identity_and_fresh_lifecycle(
    *,
    occurrence_identity: (
        batch_backend.V075BatchNativeOccurrenceIdentityV1
    ),
    observer_lifecycle: (
        lifecycle.V075ParentOwnedMultistageObserverLifecycleV1
    ),
) -> lifecycle.V075OpenMultistageLifecycleBindingV1:
    if (
        type(occurrence_identity)
        is not batch_backend.V075BatchNativeOccurrenceIdentityV1
        or type(observer_lifecycle)
        is not lifecycle.V075ParentOwnedMultistageObserverLifecycleV1
    ):
        _fail("direct pipeline rejects duck-typed identity/lifecycle")
    binding = observer_lifecycle.open_binding
    if (
        occurrence_identity.arm
        is not worker.V075WorkerArmV1.MATCHED_DIRECT_GROUND
        or occurrence_identity.source_transport_id is not None
        or occurrence_identity.threshold_profile_id
        != worker.V075WorkerThresholdProfileV1().threshold_profile_id
        or occurrence_identity.cap_profile_id
        != binding.route_cap_profile_id
        or occurrence_identity.occurrence_id != binding.occurrence_id
        or occurrence_identity.target_tape_namespace_id
        != binding.target_tape_namespace_id
        or occurrence_identity.context_id != binding.context_id
        or binding.arm
        is not worker.V075WorkerArmV1.MATCHED_DIRECT_GROUND
        or observer_lifecycle.batches
        or observer_lifecycle.events
        or observer_lifecycle.aggregate_support_evidence
    ):
        _fail(
            "direct pipeline identity/lifecycle is used, transplanted, "
            "non-direct, or not pre-sampling"
        )
    return binding


def _checkpoint(
    *,
    occurrence_identity: (
        batch_backend.V075BatchNativeOccurrenceIdentityV1
    ),
    batches: tuple[batched.V075SignedBatchedObservationV1, ...],
    checkpoint: int,
) -> V075DirectCheckpointReplayV1:
    request = batch_backend.freeze_v075_batch_native_backend_request_v1(
        arm=worker.V075WorkerArmV1.MATCHED_DIRECT_GROUND,
        occurrence_ordinal=occurrence_identity.occurrence_ordinal,
        batches=batches,
        occurrence_identity=occurrence_identity,
    )
    backend_result = (
        batch_backend.compile_v075_batch_native_statistical_backend_v1(
            request
        )
    )
    planner_result = batch_backend.plan_v075_batch_native_route_v1(
        backend_result
    )
    return V075DirectCheckpointReplayV1(
        checkpoint,
        request,
        backend_result,
        planner_result,
    )


def execute_v075_integrated_direct_occurrence_preclose_v1(
    *,
    occurrence_identity: (
        batch_backend.V075BatchNativeOccurrenceIdentityV1
    ),
    observer_lifecycle: (
        lifecycle.V075ParentOwnedMultistageObserverLifecycleV1
    ),
) -> V075IntegratedDirectOccurrenceResultV1:
    """Execute the direct route and leave its parent lifecycle open."""

    binding = _validate_identity_and_fresh_lifecycle(
        occurrence_identity=occurrence_identity,
        observer_lifecycle=observer_lifecycle,
    )
    namespace = binding.namespace
    context = _context_from_binding(binding)
    caps = binding.route_cap_profile
    root = graph.root_catalogue_v1(context)

    root_batches = []
    for action in root.actions:
        row_binding = graph.observation_row_binding_v1(
            context,
            root,
            action,
        )
        stream = _bootstrap_stream(
            namespace=namespace,
            row_binding=row_binding,
        )
        root_batches.append(
            observer_lifecycle.execute_batch_v1(
                stream_identity=stream,
                accepted_draw_start=1,
                accepted_draw_count=caps.initial_discovery_draws_per_row,
                accepted_draw_cap=caps.initial_discovery_draws_per_row,
            )
        )
    root_batches_tuple = tuple(root_batches)
    root_bindings, child_bindings = _root_and_child_bindings(
        context=context,
        root_batches=root_batches_tuple,
    )
    physical_rows = len(root.actions) + sum(
        len(item.row_bindings) for item in child_bindings
    )
    if physical_rows > context.maximum_physical_rows_per_confidence_epoch:
        raise V075IntegratedDirectPhysicalRowCapExceeded(
            occurrence_id=occurrence_identity.occurrence_id,
            observed_physical_rows=physical_rows,
            maximum_physical_rows=(
                context.maximum_physical_rows_per_confidence_epoch
            ),
            retained_root_batch_ids=tuple(
                sorted(item.batch_id for item in root_batches_tuple)
            ),
        )

    child_batches = []
    for child in child_bindings:
        for row_binding in child.row_bindings:
            stream = _bootstrap_stream(
                namespace=namespace,
                row_binding=row_binding,
            )
            child_batches.append(
                observer_lifecycle.execute_batch_v1(
                    stream_identity=stream,
                    accepted_draw_start=1,
                    accepted_draw_count=(
                        caps.new_child_discovery_draws_per_row
                    ),
                    accepted_draw_cap=(
                        caps.new_child_discovery_draws_per_row
                    ),
                )
            )

    discovery_batches = (*root_batches_tuple, *child_batches)
    validation_streams = []
    for discovery in discovery_batches:
        evidence = (
            observer_lifecycle.freeze_aggregate_support_evidence_v1(
                discovery_batch=discovery,
                selected_outcome_ids=_canonical_support_outcome_ids(
                    context=context,
                    batch=discovery,
                ),
            )
        )
        stream = _validation_stream(
            namespace=namespace,
            discovery_stream=discovery.request.stream_identity,
            evidence=evidence,
        )
        observer_lifecycle.register_validation_support_epoch_v1(
            stream_identity=stream
        )
        validation_streams.append(stream)

    history = []
    prior_checkpoint = 0
    maximum_checkpoint = caps.direct_validation_checkpoints[-1]
    for checkpoint in caps.direct_validation_checkpoints:
        increment = checkpoint - prior_checkpoint
        for stream in validation_streams:
            observer_lifecycle.execute_batch_v1(
                stream_identity=stream,
                accepted_draw_start=prior_checkpoint + 1,
                accepted_draw_count=increment,
                accepted_draw_cap=maximum_checkpoint,
            )
        current = _checkpoint(
            occurrence_identity=occurrence_identity,
            batches=observer_lifecycle.batches,
            checkpoint=checkpoint,
        )
        history.append(current)
        if current.planner_result.ready_for_exact_total_lift:
            break
        prior_checkpoint = checkpoint

    history_tuple = tuple(history)
    terminal = (
        V075IntegratedDirectTerminalV1.READY_FOR_EXACT_TOTAL_LIFT
        if history_tuple[-1].planner_result.ready_for_exact_total_lift
        else (
            V075IntegratedDirectTerminalV1
            .DIRECT_CHECKPOINT_CAP_EXHAUSTED
        )
    )
    work = _work(
        occurrence_id=occurrence_identity.occurrence_id,
        root_batches=root_batches_tuple,
        child_bindings=child_bindings,
        discovery_batches=tuple(discovery_batches),
        evidence=observer_lifecycle.aggregate_support_evidence,
        final_batches=observer_lifecycle.batches,
        history=history_tuple,
    )
    return V075IntegratedDirectOccurrenceResultV1(
        _RESULT_ISSUER,
        occurrence_identity,
        binding,
        observer_lifecycle.batches,
        observer_lifecycle.events,
        observer_lifecycle.aggregate_support_evidence,
        root_bindings,
        child_bindings,
        history_tuple,
        terminal,
        work,
    )


def _replay_event_order(
    *,
    result: V075IntegratedDirectOccurrenceResultV1,
    discovery_batches: tuple[
        batched.V075SignedBatchedObservationV1, ...
    ],
    evidence_by_discovery: Mapping[
        str, tuple[graph.V075BatchAggregateSupportEvidenceV1, ...]
    ],
    validation_batches: tuple[
        batched.V075SignedBatchedObservationV1, ...
    ],
) -> None:
    expected_length = (
        len(discovery_batches) * 2 + len(validation_batches)
    )
    if len(result.events) != expected_length:
        _fail("direct lifecycle event registry is incomplete")
    prior = None
    for index, event in enumerate(result.events, 1):
        if event.sequence_number != index:
            _fail("direct lifecycle event sequence is reordered")
        if prior is not None and event.previous_event_id != prior.event_id:
            _fail("direct lifecycle event hash chain is broken")
        prior = event
    offset = 0
    for event, batch in zip(
        result.events[: len(discovery_batches)],
        discovery_batches,
        strict=True,
    ):
        if (
            event.kind
            is not lifecycle.V075LifecycleEventKindV1.DISCOVERY_BATCH
            or event.batch_id != batch.batch_id
            or event.request_id != batch.request.request_id
            or event.stream_id
            != batch.request.stream_identity.stream_id
            or event.row_binding_id
            != batch.request.stream_identity.row_binding_id
        ):
            _fail("direct discovery event differs from batch emission")
    offset += len(discovery_batches)
    for event, batch in zip(
        result.events[offset : offset + len(discovery_batches)],
        discovery_batches,
        strict=True,
    ):
        evidence = evidence_by_discovery[batch.batch_id]
        if (
            event.kind
            is not lifecycle.V075LifecycleEventKindV1.SUPPORT_FREEZE
            or event.row_binding_id
            != batch.request.stream_identity.row_binding_id
            or event.aggregate_support_evidence_ids
            != tuple(item.evidence_id for item in evidence)
            or event.source_discovery_batch_ids != (batch.batch_id,)
        ):
            _fail("direct support-freeze event is incomplete or reordered")
    offset += len(discovery_batches)
    for event, batch in zip(
        result.events[offset:],
        validation_batches,
        strict=True,
    ):
        if (
            event.kind
            is not lifecycle.V075LifecycleEventKindV1.VALIDATION_BATCH
            or event.batch_id != batch.batch_id
            or event.request_id != batch.request.request_id
            or event.stream_id
            != batch.request.stream_identity.stream_id
            or event.row_binding_id
            != batch.request.stream_identity.row_binding_id
        ):
            _fail("direct validation event differs from batch emission")


def _replay_v075_integrated_direct_result_v1(
    claimed: V075IntegratedDirectOccurrenceResultV1,
) -> V075IntegratedDirectOccurrenceResultV1:
    if type(claimed) is not V075IntegratedDirectOccurrenceResultV1:
        _fail("direct public replay rejects duck-typed results")
    identity = claimed.occurrence_identity
    binding = claimed.open_binding
    context = _context_from_binding(binding)
    namespace = binding.namespace
    if (
        identity.arm
        is not worker.V075WorkerArmV1.MATCHED_DIRECT_GROUND
        or identity.occurrence_id != binding.occurrence_id
        or identity.context_id != context.context_id
        or identity.target_tape_namespace_id
        != namespace.target_tape_namespace_id
        or identity.cap_profile_id != binding.route_cap_profile_id
    ):
        _fail("direct replay identity/open binding was transplanted")
    for item in claimed.batches:
        batched.verify_v075_signed_batched_observation_v1(item)
    if len({item.batch_id for item in claimed.batches}) != len(
        claimed.batches
    ):
        _fail("direct replay contains a duplicate signed batch")

    root = graph.root_catalogue_v1(context)
    discovery = tuple(
        item
        for item in claimed.batches
        if item.request.stream_identity.lane
        is graph.V075ObservationLaneV1.DISCOVERY
    )
    validation = tuple(
        item
        for item in claimed.batches
        if item.request.stream_identity.lane
        is graph.V075ObservationLaneV1.VALIDATION
    )
    if (
        claimed.batches[: len(discovery)] != discovery
        or not validation
        or any(
            (
                item.request.stream_identity.target_tape_namespace_id,
                item.request.stream_identity.context_id,
                item.request.stream_identity.arm,
                item.request.session_public_id,
            )
            != (
                binding.target_tape_namespace_id,
                binding.context_id,
                binding.arm.value,
                binding.session_public_id,
            )
            for item in claimed.batches
        )
    ):
        _fail("direct batch registry crosses identity or causal phases")
    root_batches = tuple(
        item
        for item in discovery
        if item.request.stream_identity.row_binding.remaining_horizon == 2
    )
    child_batches = tuple(
        item
        for item in discovery
        if item.request.stream_identity.row_binding.remaining_horizon == 1
    )
    expected_root_rows = tuple(
        graph.observation_row_binding_v1(
            context,
            root,
            action,
        )
        for action in root.actions
    )
    if (
        tuple(
            item.request.stream_identity.row_binding.action
            for item in root_batches
        )
        != root.actions
        or len(root_batches) != len(root.actions)
        or tuple(
            item.request.stream_identity for item in root_batches
        )
        != tuple(
            _bootstrap_stream(
                namespace=namespace,
                row_binding=row,
            )
            for row in expected_root_rows
        )
        or any(
            item.request.accepted_draw_start != 1
            or item.request.accepted_draw_count
            != binding.route_cap_profile.initial_discovery_draws_per_row
            or item.request.accepted_draw_cap
            != binding.route_cap_profile.initial_discovery_draws_per_row
            for item in root_batches
        )
    ):
        _fail("direct root discovery omitted or reordered a legal action")
    roots, children = _root_and_child_bindings(
        context=context,
        root_batches=root_batches,
    )
    expected_child_rows = tuple(
        item
        for child in children
        for item in child.row_bindings
    )
    if (
        tuple(
            item.request.stream_identity.row_binding.row_binding_id
            for item in child_batches
        )
        != tuple(item.row_binding_id for item in expected_child_rows)
        or tuple(
            item.request.stream_identity for item in child_batches
        )
        != tuple(
            _bootstrap_stream(
                namespace=namespace,
                row_binding=row,
            )
            for row in expected_child_rows
        )
        or any(
            item.request.accepted_draw_start != 1
            or item.request.accepted_draw_count
            != binding.route_cap_profile.new_child_discovery_draws_per_row
            or item.request.accepted_draw_cap
            != binding.route_cap_profile.new_child_discovery_draws_per_row
            for item in child_batches
        )
        or len(discovery)
        > context.maximum_physical_rows_per_confidence_epoch
    ):
        _fail(
            "direct child discovery omitted, added, reordered, or "
            "over-capped a complete catalogue"
        )
    if (
        roots != claimed.root_child_bindings
        or children != claimed.child_catalogue_bindings
    ):
        _fail("claimed direct root/child closure differs from public replay")

    discovery_by_row = {
        item.request.stream_identity.row_binding_id: item
        for item in discovery
    }
    validation_by_stream: dict[
        str, list[batched.V075SignedBatchedObservationV1]
    ] = {}
    validation_stream_by_row = {}
    for item in validation:
        stream = item.request.stream_identity
        validation_by_stream.setdefault(stream.stream_id, []).append(item)
        prior = validation_stream_by_row.get(stream.row_binding_id)
        if prior is not None and prior != stream:
            _fail("direct row changed validation stream identity")
        validation_stream_by_row[stream.row_binding_id] = stream
    if set(validation_stream_by_row) != set(discovery_by_row):
        _fail("direct validation registry omits or adds a discovered row")
    evidence_by_discovery = {}
    all_evidence = []
    for row_id, source in discovery_by_row.items():
        stream = validation_stream_by_row[row_id]
        evidence = tuple(
            item
            for item in stream.pairing_authority.support_chain.leaf.evidence
            if type(item)
            is graph.V075BatchAggregateSupportEvidenceV1
        )
        expected_outcomes = _canonical_support_outcome_ids(
            context=context,
            batch=source,
        )
        if (
            len(evidence)
            != len(stream.pairing_authority.support_chain.leaf.evidence)
            or stream
            != _validation_stream(
                namespace=namespace,
                discovery_stream=source.request.stream_identity,
                evidence=evidence,
            )
            or tuple(
                sorted(item.discovery_outcome_id for item in evidence)
            )
            != expected_outcomes
            or any(
                item.discovery_batch_id != source.batch_id
                or item.discovery_request_id
                != source.request.request_id
                or item.row_binding
                != source.request.stream_identity.row_binding
                for item in evidence
            )
        ):
            _fail(
                "direct support freeze omitted or added a distinct "
                "discovery state"
            )
        evidence_by_discovery[source.batch_id] = evidence
        all_evidence.extend(evidence)
    canonical_evidence = tuple(
        sorted(all_evidence, key=lambda item: item.evidence_id)
    )
    if canonical_evidence != claimed.aggregate_support_evidence:
        _fail("direct aggregate support-evidence registry changed")

    stream_order = tuple(
        validation_stream_by_row[
            item.request.stream_identity.row_binding_id
        ]
        for item in discovery
    )
    checkpoints = binding.route_cap_profile.direct_validation_checkpoints
    block_width = len(stream_order)
    if (
        not validation
        or len(validation) % block_width
        or len(validation) // block_width not in range(1, len(checkpoints) + 1)
    ):
        _fail("direct validation checkpoint blocks are incomplete")
    completed = len(validation) // block_width
    prior_checkpoint = 0
    for block_index in range(completed):
        checkpoint = checkpoints[block_index]
        block = validation[
            block_index * block_width : (block_index + 1) * block_width
        ]
        if (
            tuple(item.request.stream_identity for item in block)
            != stream_order
            or any(
                item.request.accepted_draw_start != prior_checkpoint + 1
                or item.request.accepted_draw_count
                != checkpoint - prior_checkpoint
                or item.request.accepted_draw_cap != checkpoints[-1]
                for item in block
            )
        ):
            _fail("direct validation checkpoint was reordered or re-capped")
        prior_checkpoint = checkpoint

    replayed_history = []
    discovery_count = len(discovery)
    for index in range(completed):
        prefix = (
            *claimed.batches[:discovery_count],
            *validation[: (index + 1) * block_width],
        )
        replayed = _checkpoint(
            occurrence_identity=identity,
            batches=tuple(prefix),
            checkpoint=checkpoints[index],
        )
        replayed_history.append(replayed)
        if (
            replayed.planner_result.ready_for_exact_total_lift
            and index + 1 != completed
        ):
            _fail("direct route continued after its first ready checkpoint")
    replayed_history_tuple = tuple(replayed_history)
    final_ready = (
        replayed_history_tuple[-1]
        .planner_result.ready_for_exact_total_lift
    )
    if not final_ready and completed != len(checkpoints):
        _fail("direct route stopped before readiness or registered cap")
    terminal = (
        V075IntegratedDirectTerminalV1.READY_FOR_EXACT_TOTAL_LIFT
        if final_ready
        else (
            V075IntegratedDirectTerminalV1
            .DIRECT_CHECKPOINT_CAP_EXHAUSTED
        )
    )
    _replay_event_order(
        result=claimed,
        discovery_batches=discovery,
        evidence_by_discovery=evidence_by_discovery,
        validation_batches=validation,
    )
    work = _work(
        occurrence_id=identity.occurrence_id,
        root_batches=root_batches,
        child_bindings=children,
        discovery_batches=discovery,
        evidence=canonical_evidence,
        final_batches=claimed.batches,
        history=replayed_history_tuple,
    )
    return V075IntegratedDirectOccurrenceResultV1(
        _RESULT_ISSUER,
        identity,
        binding,
        claimed.batches,
        claimed.events,
        canonical_evidence,
        roots,
        children,
        replayed_history_tuple,
        terminal,
        work,
    )


_VERIFICATION_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075IntegratedDirectOccurrenceVerificationV1:
    _issuer: object = field(repr=False, compare=False)
    result_id: str
    occurrence_id: str
    terminal: V075IntegratedDirectTerminalV1
    checkpoint_count: int
    batch_count: int
    accepted_draw_count: int
    work_id: str
    _verification_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value, label in (
            (self.result_id, "verified direct result"),
            (self.occurrence_id, "verified direct occurrence"),
            (self.work_id, "verified direct work"),
        ):
            _cid(value, label)
        if (
            self._issuer is not _VERIFICATION_ISSUER
            or type(self.terminal) is not V075IntegratedDirectTerminalV1
            or type(self.checkpoint_count) is not int
            or self.checkpoint_count <= 0
            or type(self.batch_count) is not int
            or self.batch_count <= 0
            or type(self.accepted_draw_count) is not int
            or self.accepted_draw_count <= 0
        ):
            _fail("direct occurrence verification is malformed")
        object.__setattr__(
            self,
            "_verification_id",
            _hash("verification", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_integrated_direct_occurrence_"
                "preclose_verification.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "result_id": self.result_id,
            "occurrence_id": self.occurrence_id,
            "terminal": self.terminal.value,
            "checkpoint_count": self.checkpoint_count,
            "batch_count": self.batch_count,
            "accepted_draw_count": self.accepted_draw_count,
            "work_id": self.work_id,
            "signed_batches_replayed": True,
            "distinct_child_closure_replayed": True,
            "complete_child_catalogues_replayed": True,
            "support_freezes_replayed": True,
            "checkpoint_history_recomputed": True,
            "backend_and_direct_planner_recomputed": True,
            "counter_vector_recomputed": True,
            "verifier_target_accessed": False,
            "occurrence_target_batches_present": True,
            "valid": True,
        }

    @property
    def verification_id(self) -> str:
        return self._verification_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "verification_id": self.verification_id,
        }


def verify_v075_integrated_direct_occurrence_preclose_v1(
    claimed: V075IntegratedDirectOccurrenceResultV1,
) -> V075IntegratedDirectOccurrenceVerificationV1:
    """Independently replay one direct result using public signed batches."""

    replayed = _replay_v075_integrated_direct_result_v1(claimed)
    if replayed != claimed or replayed.result_id != claimed.result_id:
        _fail("claimed direct result differs from exact public replay")
    return V075IntegratedDirectOccurrenceVerificationV1(
        _VERIFICATION_ISSUER,
        replayed.result_id,
        replayed.occurrence_identity.occurrence_id,
        replayed.terminal,
        len(replayed.checkpoint_history),
        len(replayed.batches),
        sum(
            item.request.accepted_draw_count
            for item in replayed.batches
        ),
        replayed.work.work_id,
    )


__all__ = [
    "DIRECT_PIPELINE_COUNTER_PATHS",
    "DOMAIN_TAGS",
    "PER_DRAW_CAPABILITY_EXPANSION_ALLOWED",
    "PROFILE_KEY",
    "PRODUCTION_INTEGRATION_READY",
    "PROPOSED_CONTRACT_VERSION",
    "SCHEMA_VERSION",
    "V075DirectCheckpointReplayV1",
    "V075DirectChildCatalogueBindingV1",
    "V075DirectRootChildrenBindingV1",
    "V075IntegratedDirectCounterV1",
    "V075IntegratedDirectOccurrenceResultV1",
    "V075IntegratedDirectOccurrenceVerificationV1",
    "V075IntegratedDirectPhysicalRowCapExceeded",
    "V075IntegratedDirectPipelineInvariantViolation",
    "V075IntegratedDirectTerminalV1",
    "V075IntegratedDirectWorkV1",
    "execute_v075_integrated_direct_occurrence_preclose_v1",
    "verify_v075_integrated_direct_occurrence_preclose_v1",
]
