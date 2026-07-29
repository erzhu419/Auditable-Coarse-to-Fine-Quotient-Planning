"""Pre-close integrated adaptive occurrence pipeline for V0-075.

The pipeline consumes one already-open, parent-owned multistage observer
lifecycle.  It freezes the pre-sampling occurrence identity and proposal
inputs, executes the complete registered root schedule, compiles and plans
from native signed aggregates, and performs at most two failed-proof-driven
adaptive rounds.  Missing children are materialized only through the exact
complete-catalogue intents issued by the round-bundle authority; otherwise
the authority may append only a registered validation-prefix promotion.

The result is deliberately pre-close and noncertificate.  It binds every
observer event, backend compilation, failed-proof frontier, authorization,
append-only round execution, planner result, counter, and terminal reason so
that the parent can close the same lifecycle and pass it to later exact-lift
and campaign authorities.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import hashlib
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes, parse_content_id
from acfqp import v075_adaptive_acquisition_proposal_authority_v1 as proposal
from acfqp import (
    v075_adaptive_acquisition_round_bundle_authority_v1 as round_bundle,
)
from acfqp import v075_batch_native_statistical_backend_v1 as backend
from acfqp import v075_batched_observer_authority_v1 as batched
from acfqp import v075_learned_support_quotient_planners_v1 as planners
from acfqp import v075_multistage_observer_lifecycle_v1 as lifecycle
from acfqp import v075_public_campaign_authority_v1 as public_authority
from acfqp import v075_public_graph_semantics_v1 as graph
from acfqp import v075_registered_occurrence_worker_v1 as worker


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "1.40.0"
PROFILE_KEY = "v075_integrated_adaptive_occurrence_pipeline_v1"
PRODUCTION_INTEGRATION_READY = False
MAX_ADAPTIVE_ROUNDS = 2
MAX_INCREMENTAL_DRAWS = 160_960
MAX_NEW_CHILD_ACTION_ROWS = 19

_ISSUER = object()

DOMAIN_TAGS = {
    "round": "acfqp:v075-integrated-occurrence-round-execution:v1",
    "counters": "acfqp:v075-integrated-occurrence-counters:v1",
    "result": "acfqp:v075-integrated-occurrence-preclose-result:v1",
    "verification": (
        "acfqp:v075-integrated-occurrence-preclose-verification:v1"
    ),
}

if len(DOMAIN_TAGS) != len(set(DOMAIN_TAGS.values())):
    raise RuntimeError("V0-075 integrated occurrence domains must be unique")


class V075IntegratedOccurrencePipelineInvariantViolation(ValueError):
    """An identity, phase, intent, cap, append, or replay invariant failed."""


def _fail(message: str) -> None:
    raise V075IntegratedOccurrencePipelineInvariantViolation(message)


def _hash(role: str, payload: Mapping[str, Any]) -> str:
    try:
        return hashlib.sha256(
            DOMAIN_TAGS[role].encode("utf-8")
            + b"\x00"
            + canonical_json_bytes(dict(payload))
        ).hexdigest()
    except (KeyError, TypeError, ValueError) as error:
        raise V075IntegratedOccurrencePipelineInvariantViolation(
            str(error)
        ) from error


def _cid(value: Any, field_name: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise V075IntegratedOccurrencePipelineInvariantViolation(
            f"{field_name} must be one lowercase SHA-256 content ID"
        ) from error


class V075IntegratedOccurrenceTerminalCodeV1(str, Enum):
    CANDIDATE_READY_FOR_EXACT_TOTAL_LIFT = (
        "CANDIDATE_READY_FOR_EXACT_TOTAL_LIFT"
    )
    NO_UNCERTAIN_PROOF_FRONTIER = "NO_UNCERTAIN_PROOF_FRONTIER"
    INCREMENTAL_CAP_EXHAUSTED = "INCREMENTAL_CAP_EXHAUSTED"
    PLANNER_SEARCH_CAP_EXHAUSTED = "PLANNER_SEARCH_CAP_EXHAUSTED"
    ADAPTIVE_ROUND_LIMIT_REACHED = "ADAPTIVE_ROUND_LIMIT_REACHED"


def _bootstrap_stream(
    *,
    namespace: public_authority.V075PublicTargetTapeNamespaceV1,
    row_binding: graph.V075ObservationRowBindingV1,
    arm: worker.V075WorkerArmV1,
) -> tuple[
    graph.V075SharedSupportEpochV1,
    graph.V075TransitionStreamIdentityV1,
]:
    root_epoch = graph.derive_shared_support_epoch_v1(
        namespace=namespace,
        row_binding=row_binding,
        epoch_index=0,
        evidence=(),
    )
    root_chain = graph.freeze_shared_support_chain_v1(
        namespace=namespace,
        row_binding=row_binding,
        epochs=(root_epoch,),
    )
    pairing = graph.freeze_five_arm_pairing_authority_v1(
        namespace=namespace,
        row_binding=row_binding,
        support_chain=root_chain,
    )
    return (
        root_epoch,
        graph.derive_transition_stream_identity_v1(
            pairing_authority=pairing,
            arm=arm.value,
        ),
    )


def _support_outcome_ids(
    discovery_batch: batched.V075SignedBatchedObservationV1,
) -> tuple[str, ...]:
    """Select every distinct observed symbolic state, without alias weight."""

    if (
        type(discovery_batch)
        is not batched.V075SignedBatchedObservationV1
        or discovery_batch.request.stream_identity.lane
        is not graph.V075ObservationLaneV1.DISCOVERY
    ):
        _fail("support selection requires one exact discovery batch")
    row = discovery_batch.request.stream_identity.row_binding
    selected_by_state: dict[str, str] = {}
    for outcome in discovery_batch.outcomes:
        try:
            state = graph.V075SymbolicGraphStateV1(
                row.context,
                outcome.next_ranks,
                outcome.failure,
            )
        except graph.V075PublicGraphSemanticsInvariantViolation as error:
            raise V075IntegratedOccurrencePipelineInvariantViolation(
                str(error)
            ) from error
        prior = selected_by_state.get(state.state_id)
        if prior is None or outcome.outcome_id < prior:
            selected_by_state[state.state_id] = outcome.outcome_id
    result = tuple(sorted(selected_by_state.values()))
    if not result:
        _fail("discovery batch exposed no symbolic support")
    return result


def _validation_stream(
    *,
    namespace: public_authority.V075PublicTargetTapeNamespaceV1,
    row_binding: graph.V075ObservationRowBindingV1,
    root_epoch: graph.V075SharedSupportEpochV1,
    evidence: tuple[graph.V075BatchAggregateSupportEvidenceV1, ...],
    arm: worker.V075WorkerArmV1,
) -> graph.V075TransitionStreamIdentityV1:
    validation_epoch = graph.derive_shared_support_epoch_v1(
        namespace=namespace,
        row_binding=row_binding,
        epoch_index=1,
        evidence=evidence,
        parent=root_epoch,
    )
    chain = graph.freeze_shared_support_chain_v1(
        namespace=namespace,
        row_binding=row_binding,
        epochs=(root_epoch, validation_epoch),
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


def _require_open_binding(
    *,
    controller: lifecycle.V075ParentOwnedMultistageObserverLifecycleV1,
    occurrence_identity: backend.V075BatchNativeOccurrenceIdentityV1,
    namespace: public_authority.V075PublicTargetTapeNamespaceV1,
    context: public_authority.V075PublicReplicateContextV1,
    arm: worker.V075WorkerArmV1,
    cap_profile: worker.V075WorkerCapProfileV1,
) -> lifecycle.V075OpenMultistageLifecycleBindingV1:
    if (
        type(controller)
        is not lifecycle.V075ParentOwnedMultistageObserverLifecycleV1
    ):
        _fail("integrated pipeline requires one exact parent-owned lifecycle")
    binding = controller.open_binding
    if (
        type(binding)
        is not lifecycle.V075OpenMultistageLifecycleBindingV1
        or binding.occurrence_id != occurrence_identity.occurrence_id
        or binding.context_id != context.context_id
        or binding.arm is not arm
        or binding.route_cap_profile != cap_profile
        or binding.namespace != namespace
        or binding.target_tape_namespace_id
        != occurrence_identity.target_tape_namespace_id
        or binding.context_id != occurrence_identity.context_id
        or binding.arm is not occurrence_identity.arm
        or binding.route_cap_profile_id
        != occurrence_identity.cap_profile_id
    ):
        _fail(
            "open lifecycle differs from the frozen occurrence identity"
        )
    return binding


def _compile_and_plan(
    *,
    occurrence_identity: backend.V075BatchNativeOccurrenceIdentityV1,
    controller: lifecycle.V075ParentOwnedMultistageObserverLifecycleV1,
    arm: worker.V075WorkerArmV1,
    occurrence_ordinal: int,
    source_prior_transport: worker.V075SourcePriorTransportV1 | None,
) -> tuple[
    backend.V075BatchNativeBackendResultV1,
    planners.V075SupportPlannerResultV1,
]:
    request = backend.freeze_v075_batch_native_backend_request_v1(
        arm=arm,
        occurrence_ordinal=occurrence_ordinal,
        batches=controller.batches,
        source_prior_transport=source_prior_transport,
        occurrence_identity=occurrence_identity,
    )
    result = backend.compile_v075_batch_native_statistical_backend_v1(
        request
    )
    return result, backend.plan_v075_batch_native_route_v1(result)


def _execute_initial_schedule(
    *,
    controller: lifecycle.V075ParentOwnedMultistageObserverLifecycleV1,
    namespace: public_authority.V075PublicTargetTapeNamespaceV1,
    schedule: proposal.V075InitialRootAcquisitionScheduleV1,
) -> None:
    discoveries = tuple(
        item
        for item in schedule.intents
        if item.kind is proposal.V075InitialIntentKindV1.ROOT_DISCOVERY
    )
    validations = tuple(
        item
        for item in schedule.intents
        if item.kind is proposal.V075InitialIntentKindV1.ROOT_VALIDATION
    )
    executed: dict[
        str,
        tuple[
            graph.V075SharedSupportEpochV1,
            batched.V075SignedBatchedObservationV1,
        ],
    ] = {}
    validation_streams: dict[str, graph.V075TransitionStreamIdentityV1] = {}
    for intent in discoveries:
        root_epoch, stream = _bootstrap_stream(
            namespace=namespace,
            row_binding=intent.row_binding,
            arm=schedule.arm,
        )
        observed = controller.execute_batch_v1(
            stream_identity=stream,
            accepted_draw_start=intent.accepted_draw_start,
            accepted_draw_count=intent.accepted_draw_count,
            accepted_draw_cap=intent.accepted_draw_cap,
        )
        executed[intent.intent_id] = (root_epoch, observed)
    for intent in validations:
        if intent.dependency_intent_id not in executed:
            _fail("initial validation dependency was reordered or transplanted")
        root_epoch, discovery = executed[intent.dependency_intent_id]
        evidence = controller.freeze_aggregate_support_evidence_v1(
            discovery_batch=discovery,
            selected_outcome_ids=_support_outcome_ids(discovery),
        )
        stream = _validation_stream(
            namespace=namespace,
            row_binding=intent.row_binding,
            root_epoch=root_epoch,
            evidence=evidence,
            arm=schedule.arm,
        )
        controller.register_validation_support_epoch_v1(
            stream_identity=stream
        )
        validation_streams[intent.intent_id] = stream
    for intent in validations:
        controller.execute_batch_v1(
            stream_identity=validation_streams[intent.intent_id],
            accepted_draw_start=intent.accepted_draw_start,
            accepted_draw_count=intent.accepted_draw_count,
            accepted_draw_cap=intent.accepted_draw_cap,
        )


def _execute_round_intents(
    *,
    controller: lifecycle.V075ParentOwnedMultistageObserverLifecycleV1,
    namespace: public_authority.V075PublicTargetTapeNamespaceV1,
    prior_result: backend.V075BatchNativeBackendResultV1,
    authorization: (
        round_bundle.V075AdaptiveRoundBundleAuthorizationV1
    ),
) -> tuple[str, ...]:
    """Execute one frozen bundle in lifecycle-causal observer order."""

    if (
        authorization.status
        is not round_bundle.V075BundleAuthorizationStatusV1.AUTHORIZED
    ):
        _fail("observer execution requires one authorized round bundle")
    controller.start_adaptive_round_v1(
        authorization.frontier.round_index
    )
    before = {item.batch_id for item in controller.batches}
    discovery_records: dict[
        str,
        tuple[
            graph.V075SharedSupportEpochV1,
            batched.V075SignedBatchedObservationV1,
        ],
    ] = {}
    new_validation_streams: dict[
        str,
        graph.V075TransitionStreamIdentityV1,
    ] = {}

    # The authorization registry remains unchanged.  Observer phase causality
    # requires every new discovery before any existing/new validation append.
    for intent in authorization.intents:
        if (
            intent.kind
            is not round_bundle.V075BundleIntentKindV1.NEW_CHILD_ROW_DISCOVERY
        ):
            continue
        root_epoch, stream = _bootstrap_stream(
            namespace=namespace,
            row_binding=intent.row_binding,
            arm=authorization.frontier.arm,
        )
        observed = controller.execute_batch_v1(
            stream_identity=stream,
            accepted_draw_start=intent.accepted_draw_start,
            accepted_draw_count=intent.accepted_draw_count,
            accepted_draw_cap=intent.accepted_draw_cap,
        )
        discovery_records[intent.intent_id] = (root_epoch, observed)

    for intent in authorization.intents:
        if (
            intent.kind
            is not round_bundle.V075BundleIntentKindV1.NEW_CHILD_ROW_VALIDATION
        ):
            continue
        dependency = discovery_records.get(intent.dependency_intent_id)
        if dependency is None:
            _fail("child validation lacks its exact discovery intent")
        root_epoch, discovery = dependency
        evidence = controller.freeze_aggregate_support_evidence_v1(
            discovery_batch=discovery,
            selected_outcome_ids=_support_outcome_ids(discovery),
        )
        stream = _validation_stream(
            namespace=namespace,
            row_binding=intent.row_binding,
            root_epoch=root_epoch,
            evidence=evidence,
            arm=authorization.frontier.arm,
        )
        controller.register_validation_support_epoch_v1(
            stream_identity=stream
        )
        new_validation_streams[intent.intent_id] = stream

    existing_streams = {
        item.request.stream_identity.stream_id:
        item.request.stream_identity
        for item in prior_result.request.batches
    }
    for intent in authorization.intents:
        if (
            intent.kind
            is round_bundle.V075BundleIntentKindV1.NEW_CHILD_ROW_DISCOVERY
        ):
            continue
        if (
            intent.kind
            is round_bundle.V075BundleIntentKindV1
            .EXISTING_VALIDATION_PREFIX_EXTENSION
        ):
            stream = existing_streams.get(intent.existing_stream_id)
            if stream is None:
                _fail("validation promotion stream was transplanted")
        else:
            stream = new_validation_streams.get(intent.intent_id)
            if stream is None:
                _fail("new child validation stream was not registered")
        controller.execute_batch_v1(
            stream_identity=stream,
            accepted_draw_start=intent.accepted_draw_start,
            accepted_draw_count=intent.accepted_draw_count,
            accepted_draw_cap=intent.accepted_draw_cap,
        )
    appended = tuple(
        sorted(
            item.batch_id
            for item in controller.batches
            if item.batch_id not in before
        )
    )
    if not appended:
        _fail("authorized round appended no observer work")
    return appended


@dataclass(frozen=True, slots=True)
class V075IntegratedAdaptiveRoundV1:
    _issuer: object = field(repr=False, compare=False)
    round_index: int
    prior_backend_result: backend.V075BatchNativeBackendResultV1
    prior_planner_result: planners.V075SupportPlannerResultV1
    frontier: round_bundle.V075AdaptiveRoundBundleFrontierV1
    authorization: round_bundle.V075AdaptiveRoundBundleAuthorizationV1
    appended_batch_ids: tuple[str, ...]
    execution: round_bundle.V075AdaptiveRoundBundleExecutionV1 | None
    resulting_backend_result: backend.V075BatchNativeBackendResultV1 | None
    resulting_planner_result: planners.V075SupportPlannerResultV1 | None

    def __post_init__(self) -> None:
        if (
            self._issuer is not _ISSUER
            or self.round_index not in (1, 2)
            or type(self.prior_backend_result)
            is not backend.V075BatchNativeBackendResultV1
            or type(self.prior_planner_result)
            is not planners.V075SupportPlannerResultV1
            or type(self.frontier)
            is not round_bundle.V075AdaptiveRoundBundleFrontierV1
            or type(self.authorization)
            is not round_bundle.V075AdaptiveRoundBundleAuthorizationV1
            or self.frontier.round_index != self.round_index
            or self.frontier.batch_result_id
            != self.prior_backend_result.result_id
            or self.frontier.planner_result_id
            != self.prior_planner_result.result_id
            or self.authorization.frontier != self.frontier
            or self.appended_batch_ids
            != tuple(sorted(set(self.appended_batch_ids)))
        ):
            _fail("integrated adaptive round is malformed or transplanted")
        authorized = (
            self.authorization.status
            is round_bundle.V075BundleAuthorizationStatusV1.AUTHORIZED
        )
        has_result = (
            self.execution is not None
            and self.resulting_backend_result is not None
            and self.resulting_planner_result is not None
        )
        if authorized != has_result:
            _fail("round authorization and execution availability disagree")
        if authorized:
            assert self.execution is not None
            assert self.resulting_backend_result is not None
            assert self.resulting_planner_result is not None
            if (
                self.execution.authorization_id
                != self.authorization.authorization_id
                or self.execution.prior_batch_result_id
                != self.prior_backend_result.result_id
                or self.execution.resulting_batch_result_id
                != self.resulting_backend_result.result_id
                or self.appended_batch_ids
                != self.execution.appended_batch_ids
                or self.resulting_planner_result.graph.backend_result
                != self.resulting_backend_result.route_native_result
            ):
                _fail("executed round identity graph is inconsistent")
        elif (
            self.appended_batch_ids
            or self.execution is not None
            or self.resulting_backend_result is not None
            or self.resulting_planner_result is not None
        ):
            _fail("nonauthorized round contains observer or planner work")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_integrated_adaptive_round.v1",
            "schema_version": SCHEMA_VERSION,
            "round_index": self.round_index,
            "prior_backend_result_id": self.prior_backend_result.result_id,
            "prior_planner_result_id": self.prior_planner_result.result_id,
            "frontier_id": self.frontier.frontier_id,
            "authorization_id": self.authorization.authorization_id,
            "authorization_status": self.authorization.status.value,
            "appended_batch_ids": list(self.appended_batch_ids),
            "execution_id": (
                None if self.execution is None else self.execution.execution_id
            ),
            "resulting_backend_result_id": (
                None
                if self.resulting_backend_result is None
                else self.resulting_backend_result.result_id
            ),
            "resulting_planner_result_id": (
                None
                if self.resulting_planner_result is None
                else self.resulting_planner_result.result_id
            ),
            "observer_execution_order": (
                "ALL_NEW_DISCOVERY_THEN_FREEZE_REGISTER_THEN_VALIDATION"
            ),
            "support_freeze_register_phase_barrier_after_intent_ids": [
                item.intent_id
                for item in self.authorization.intents
                if item.kind
                is round_bundle.V075BundleIntentKindV1
                .NEW_CHILD_ROW_DISCOVERY
            ],
            "authorization_intent_registry_reordered": False,
        }

    @property
    def round_id(self) -> str:
        return _hash("round", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "frontier": self.frontier.to_document(),
            "authorization": self.authorization.to_document(),
            "execution": (
                None if self.execution is None else self.execution.to_document()
            ),
            "round_id": self.round_id,
        }


@dataclass(frozen=True, slots=True)
class V075IntegratedOccurrenceCountersV1:
    _issuer: object = field(repr=False, compare=False)
    final_backend_result_id: str
    accepted_draws: int
    discovery_draws: int
    validation_draws: int
    incremental_draws: int
    observer_batches: int
    lifecycle_events: int
    aggregate_support_evidence: int
    adaptive_rounds_considered: int
    adaptive_rounds_authorized: int
    adaptive_rounds_executed: int
    child_action_rows_materialized: int
    backend_compilations: int
    planner_invocations: int
    process_launches: int = 0

    def __post_init__(self) -> None:
        _cid(self.final_backend_result_id, "counter final backend result")
        values = (
            self.accepted_draws,
            self.discovery_draws,
            self.validation_draws,
            self.incremental_draws,
            self.observer_batches,
            self.lifecycle_events,
            self.aggregate_support_evidence,
            self.adaptive_rounds_considered,
            self.adaptive_rounds_authorized,
            self.adaptive_rounds_executed,
            self.child_action_rows_materialized,
            self.backend_compilations,
            self.planner_invocations,
            self.process_launches,
        )
        if (
            self._issuer is not _ISSUER
            or any(type(item) is not int or item < 0 for item in values)
            or self.accepted_draws
            != self.discovery_draws + self.validation_draws
            or self.incremental_draws > MAX_INCREMENTAL_DRAWS
            or self.child_action_rows_materialized
            > MAX_NEW_CHILD_ACTION_ROWS
            or not 0
            <= self.adaptive_rounds_executed
            <= self.adaptive_rounds_authorized
            <= self.adaptive_rounds_considered
            <= MAX_ADAPTIVE_ROUNDS
            or self.backend_compilations
            != 1 + self.adaptive_rounds_executed
            or self.planner_invocations != self.backend_compilations
            or self.process_launches != 0
        ):
            _fail("integrated occurrence counters are inconsistent or over cap")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_integrated_occurrence_counters.v1",
            "schema_version": SCHEMA_VERSION,
            "final_backend_result_id": self.final_backend_result_id,
            "accepted_draws": self.accepted_draws,
            "discovery_draws": self.discovery_draws,
            "validation_draws": self.validation_draws,
            "incremental_draws": self.incremental_draws,
            "maximum_incremental_draws": MAX_INCREMENTAL_DRAWS,
            "observer_batches": self.observer_batches,
            "lifecycle_events": self.lifecycle_events,
            "aggregate_support_evidence": self.aggregate_support_evidence,
            "adaptive_rounds_considered": self.adaptive_rounds_considered,
            "adaptive_rounds_authorized": self.adaptive_rounds_authorized,
            "adaptive_rounds_executed": self.adaptive_rounds_executed,
            "child_action_rows_materialized": (
                self.child_action_rows_materialized
            ),
            "maximum_child_action_rows": MAX_NEW_CHILD_ACTION_ROWS,
            "backend_compilations": self.backend_compilations,
            "planner_invocations": self.planner_invocations,
            "process_launches": self.process_launches,
            "per_draw_capability_expansion": False,
        }

    @property
    def counters_id(self) -> str:
        return _hash("counters", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "counters_id": self.counters_id}


def _freeze_counters(
    *,
    final_backend: backend.V075BatchNativeBackendResultV1,
    rounds: tuple[V075IntegratedAdaptiveRoundV1, ...],
    events: tuple[lifecycle.V075MultistageLifecycleEventV1, ...],
) -> V075IntegratedOccurrenceCountersV1:
    batches = final_backend.request.batches
    discovery_draws = sum(
        item.request.accepted_draw_count
        for item in batches
        if item.request.stream_identity.lane
        is graph.V075ObservationLaneV1.DISCOVERY
    )
    validation_draws = sum(
        item.request.accepted_draw_count
        for item in batches
        if item.request.stream_identity.lane
        is graph.V075ObservationLaneV1.VALIDATION
    )
    accounting = round_bundle.replay_v075_incremental_accounting_v1(
        final_backend
    )
    return V075IntegratedOccurrenceCountersV1(
        _ISSUER,
        final_backend.result_id,
        discovery_draws + validation_draws,
        discovery_draws,
        validation_draws,
        accounting.incremental_draws_used,
        len(batches),
        len(events),
        len(final_backend.aggregate_support_evidence_ids),
        len(rounds),
        sum(
            item.authorization.status
            is round_bundle.V075BundleAuthorizationStatusV1.AUTHORIZED
            for item in rounds
        ),
        sum(item.execution is not None for item in rounds),
        len(accounting.new_child_action_row_ids),
        1 + sum(item.execution is not None for item in rounds),
        1 + sum(item.execution is not None for item in rounds),
    )


@dataclass(frozen=True, slots=True)
class V075IntegratedOccurrencePrecloseResultV1:
    _issuer: object = field(repr=False, compare=False)
    open_lifecycle_binding: lifecycle.V075OpenMultistageLifecycleBindingV1
    occurrence_identity: backend.V075BatchNativeOccurrenceIdentityV1
    source_view: proposal.V075SourceProposalViewV1
    initial_schedule: proposal.V075InitialRootAcquisitionScheduleV1
    initial_backend_result: backend.V075BatchNativeBackendResultV1
    initial_planner_result: planners.V075SupportPlannerResultV1
    rounds: tuple[V075IntegratedAdaptiveRoundV1, ...]
    final_backend_result: backend.V075BatchNativeBackendResultV1
    final_planner_result: planners.V075SupportPlannerResultV1
    lifecycle_events: tuple[lifecycle.V075MultistageLifecycleEventV1, ...]
    counters: V075IntegratedOccurrenceCountersV1
    terminal_code: V075IntegratedOccurrenceTerminalCodeV1

    def __post_init__(self) -> None:
        if (
            self._issuer is not _ISSUER
            or type(self.open_lifecycle_binding)
            is not lifecycle.V075OpenMultistageLifecycleBindingV1
            or type(self.occurrence_identity)
            is not backend.V075BatchNativeOccurrenceIdentityV1
            or type(self.source_view) is not proposal.V075SourceProposalViewV1
            or type(self.initial_schedule)
            is not proposal.V075InitialRootAcquisitionScheduleV1
            or type(self.initial_backend_result)
            is not backend.V075BatchNativeBackendResultV1
            or type(self.initial_planner_result)
            is not planners.V075SupportPlannerResultV1
            or type(self.rounds) is not tuple
            or type(self.final_backend_result)
            is not backend.V075BatchNativeBackendResultV1
            or type(self.final_planner_result)
            is not planners.V075SupportPlannerResultV1
            or type(self.lifecycle_events) is not tuple
            or type(self.counters)
            is not V075IntegratedOccurrenceCountersV1
            or type(self.terminal_code)
            is not V075IntegratedOccurrenceTerminalCodeV1
        ):
            _fail("integrated pre-close result is untyped")
        if (
            self.open_lifecycle_binding.occurrence_id
            != self.occurrence_identity.occurrence_id
            or self.initial_backend_result.request.occurrence_identity
            != self.occurrence_identity
            or self.initial_backend_result.request.arm
            is not self.source_view.arm
            or self.initial_schedule.arm is not self.source_view.arm
            or self.initial_schedule.context.context_id
            != self.occurrence_identity.context_id
            or self.initial_planner_result.graph.backend_result
            != self.initial_backend_result.route_native_result
            or tuple(item.round_index for item in self.rounds)
            != tuple(range(1, len(self.rounds) + 1))
            or len(self.rounds) > MAX_ADAPTIVE_ROUNDS
        ):
            _fail("integrated pre-close identity or round chain is inconsistent")
        prior_backend = self.initial_backend_result
        prior_planner = self.initial_planner_result
        for item in self.rounds:
            if (
                item.prior_backend_result != prior_backend
                or item.prior_planner_result != prior_planner
            ):
                _fail("integrated rounds are gapped, reordered, or transplanted")
            if item.resulting_backend_result is not None:
                assert item.resulting_planner_result is not None
                prior_backend = item.resulting_backend_result
                prior_planner = item.resulting_planner_result
        if (
            self.final_backend_result != prior_backend
            or self.final_planner_result != prior_planner
            or self.counters.final_backend_result_id
            != self.final_backend_result.result_id
            or self.final_backend_result.request.occurrence_identity
            != self.occurrence_identity
        ):
            _fail("integrated final artifact does not close its round chain")
        event_ids = tuple(item.event_id for item in self.lifecycle_events)
        if (
            any(
                type(item) is not lifecycle.V075MultistageLifecycleEventV1
                for item in self.lifecycle_events
            )
            or tuple(item.sequence_number for item in self.lifecycle_events)
            != tuple(range(1, len(self.lifecycle_events) + 1))
            or len(set(event_ids)) != len(event_ids)
            or {
                item.batch_id
                for item in self.lifecycle_events
                if item.batch_id is not None
            }
            != {
                item.batch_id
                for item in self.final_backend_result.request.batches
            }
        ):
            _fail("pre-close lifecycle event registry is incomplete or reordered")
        ready = self.final_planner_result.ready_for_exact_total_lift
        expected_terminal = None
        if ready:
            expected_terminal = (
                V075IntegratedOccurrenceTerminalCodeV1
                .CANDIDATE_READY_FOR_EXACT_TOTAL_LIFT
            )
        elif (
            self.final_planner_result.status
            is planners.V075PlannerStatusV1.SEARCH_CAP_EXHAUSTED
        ):
            expected_terminal = (
                V075IntegratedOccurrenceTerminalCodeV1
                .PLANNER_SEARCH_CAP_EXHAUSTED
            )
        elif self.rounds and self.rounds[-1].execution is None:
            status = self.rounds[-1].authorization.status
            expected_terminal = (
                V075IntegratedOccurrenceTerminalCodeV1
                .NO_UNCERTAIN_PROOF_FRONTIER
                if status
                is round_bundle.V075BundleAuthorizationStatusV1
                .NO_UNCERTAIN_PROOF_FRONTIER
                else V075IntegratedOccurrenceTerminalCodeV1
                .INCREMENTAL_CAP_EXHAUSTED
            )
        elif len(self.rounds) == MAX_ADAPTIVE_ROUNDS:
            expected_terminal = (
                V075IntegratedOccurrenceTerminalCodeV1
                .ADAPTIVE_ROUND_LIMIT_REACHED
            )
        if self.terminal_code is not expected_terminal:
            _fail("integrated terminal code differs from exact state replay")

    @property
    def ready_for_exact_total_lift(self) -> bool:
        return (
            self.terminal_code
            is V075IntegratedOccurrenceTerminalCodeV1
            .CANDIDATE_READY_FOR_EXACT_TOTAL_LIFT
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_integrated_occurrence_preclose_result.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "open_lifecycle_binding_id": (
                self.open_lifecycle_binding.binding_id
            ),
            "occurrence_identity_id": (
                self.occurrence_identity.occurrence_id
            ),
            "source_view_id": self.source_view.source_view_id,
            "initial_schedule_id": self.initial_schedule.schedule_id,
            "initial_backend_result_id": self.initial_backend_result.result_id,
            "initial_planner_result_id": self.initial_planner_result.result_id,
            "round_ids": [item.round_id for item in self.rounds],
            "final_backend_result_id": self.final_backend_result.result_id,
            "final_planner_result_id": self.final_planner_result.result_id,
            "lifecycle_event_ids": [
                item.event_id for item in self.lifecycle_events
            ],
            "counters_id": self.counters.counters_id,
            "terminal_code": self.terminal_code.value,
            "ready_for_exact_total_lift": self.ready_for_exact_total_lift,
            "artifact_scope": "PRE_CLOSE_OPERATIONAL_INTERMEDIATE",
            "scientific_plan_certificate": False,
            "occurrence_closed": False,
            "production_integration_ready": False,
        }

    @property
    def result_id(self) -> str:
        return _hash("result", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "open_lifecycle_binding": (
                self.open_lifecycle_binding.to_document()
            ),
            "occurrence_identity": self.occurrence_identity.to_document(),
            "source_view": self.source_view.to_document(),
            "initial_schedule": self.initial_schedule.to_document(),
            "rounds": [item.to_document() for item in self.rounds],
            "counters": self.counters.to_document(),
            "result_id": self.result_id,
        }

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())


@dataclass(frozen=True, slots=True)
class V075IntegratedOccurrenceVerificationV1:
    result_id: str
    occurrence_id: str
    final_backend_result_id: str
    final_planner_result_id: str
    terminal_code: V075IntegratedOccurrenceTerminalCodeV1
    replayed_round_count: int

    def __post_init__(self) -> None:
        for value, name in (
            (self.result_id, "verified integrated result"),
            (self.occurrence_id, "verified occurrence"),
            (self.final_backend_result_id, "verified final backend"),
            (self.final_planner_result_id, "verified final planner"),
        ):
            _cid(value, name)
        if (
            type(self.terminal_code)
            is not V075IntegratedOccurrenceTerminalCodeV1
            or type(self.replayed_round_count) is not int
            or self.replayed_round_count not in range(MAX_ADAPTIVE_ROUNDS + 1)
        ):
            _fail("integrated occurrence verification is malformed")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_integrated_occurrence_preclose_verification.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "result_id": self.result_id,
            "occurrence_id": self.occurrence_id,
            "final_backend_result_id": self.final_backend_result_id,
            "final_planner_result_id": self.final_planner_result_id,
            "terminal_code": self.terminal_code.value,
            "replayed_round_count": self.replayed_round_count,
            "exact_public_semantic_replay": True,
        }

    @property
    def verification_id(self) -> str:
        return _hash("verification", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "verification_id": self.verification_id}


def _terminal_from_state(
    *,
    planner_result: planners.V075SupportPlannerResultV1,
    rounds: tuple[V075IntegratedAdaptiveRoundV1, ...],
) -> V075IntegratedOccurrenceTerminalCodeV1 | None:
    if planner_result.ready_for_exact_total_lift:
        return (
            V075IntegratedOccurrenceTerminalCodeV1
            .CANDIDATE_READY_FOR_EXACT_TOTAL_LIFT
        )
    if (
        planner_result.status
        is planners.V075PlannerStatusV1.SEARCH_CAP_EXHAUSTED
    ):
        return (
            V075IntegratedOccurrenceTerminalCodeV1
            .PLANNER_SEARCH_CAP_EXHAUSTED
        )
    if rounds and rounds[-1].execution is None:
        return (
            V075IntegratedOccurrenceTerminalCodeV1
            .NO_UNCERTAIN_PROOF_FRONTIER
            if rounds[-1].authorization.status
            is round_bundle.V075BundleAuthorizationStatusV1
            .NO_UNCERTAIN_PROOF_FRONTIER
            else V075IntegratedOccurrenceTerminalCodeV1
            .INCREMENTAL_CAP_EXHAUSTED
        )
    if len(rounds) == MAX_ADAPTIVE_ROUNDS:
        return (
            V075IntegratedOccurrenceTerminalCodeV1
            .ADAPTIVE_ROUND_LIMIT_REACHED
        )
    return None


def run_v075_integrated_adaptive_occurrence_pipeline_v1(
    *,
    controller: lifecycle.V075ParentOwnedMultistageObserverLifecycleV1,
    namespace: public_authority.V075PublicTargetTapeNamespaceV1,
    context: public_authority.V075PublicReplicateContextV1,
    arm: worker.V075WorkerArmV1,
    occurrence_ordinal: int,
    source_prior_transport: worker.V075SourcePriorTransportV1 | None = None,
) -> V075IntegratedOccurrencePrecloseResultV1:
    """Run the registered adaptive route through its pre-close terminal."""

    if (
        type(namespace)
        is not public_authority.V075PublicTargetTapeNamespaceV1
        or type(context)
        is not public_authority.V075PublicReplicateContextV1
        or context not in namespace.family.replicate_contexts
        or type(arm) is not worker.V075WorkerArmV1
        or arm is worker.V075WorkerArmV1.MATCHED_DIRECT_GROUND
        or type(occurrence_ordinal) is not int
        or occurrence_ordinal < 0
        or (
            source_prior_transport is not None
            and type(source_prior_transport)
            is not worker.V075SourcePriorTransportV1
        )
        or (
            source_prior_transport is not None
        )
        != (arm is worker.V075WorkerArmV1.SOURCE_CONSENSUS_PRIOR)
    ):
        _fail("integrated pipeline inputs are untyped or arm-transplanted")
    if controller.batches or controller.events:
        _fail("integrated pipeline requires one unused open lifecycle")
    threshold = worker.V075WorkerThresholdProfileV1()
    caps = worker.V075WorkerCapProfileV1()
    occurrence_identity = (
        backend.freeze_v075_batch_native_occurrence_identity_v1(
            namespace=namespace,
            context=context,
            arm=arm,
            occurrence_ordinal=occurrence_ordinal,
            threshold_profile=threshold,
            cap_profile=caps,
            source_prior_transport=source_prior_transport,
        )
    )
    open_binding = _require_open_binding(
        controller=controller,
        occurrence_identity=occurrence_identity,
        namespace=namespace,
        context=context,
        arm=arm,
        cap_profile=caps,
    )
    source_view = proposal.freeze_v075_source_proposal_view_v1(
        arm=arm,
        source_transport=source_prior_transport,
    )
    schedule = proposal.freeze_v075_initial_root_acquisition_schedule_v1(
        context=context,
        arm=arm,
    )
    _execute_initial_schedule(
        controller=controller,
        namespace=namespace,
        schedule=schedule,
    )
    _require_open_binding(
        controller=controller,
        occurrence_identity=occurrence_identity,
        namespace=namespace,
        context=context,
        arm=arm,
        cap_profile=caps,
    )
    initial_backend, initial_planner = _compile_and_plan(
        occurrence_identity=occurrence_identity,
        controller=controller,
        arm=arm,
        occurrence_ordinal=occurrence_ordinal,
        source_prior_transport=source_prior_transport,
    )
    current_backend = initial_backend
    current_planner = initial_planner
    rounds: list[V075IntegratedAdaptiveRoundV1] = []
    prior_execution: round_bundle.V075AdaptiveRoundBundleExecutionV1 | None = (
        None
    )

    while _terminal_from_state(
        planner_result=current_planner,
        rounds=tuple(rounds),
    ) is None:
        round_index = len(rounds) + 1
        frontier = (
            round_bundle.freeze_v075_adaptive_round_bundle_frontier_v1(
                batch_result=current_backend,
                planner_result=current_planner,
                source_view=source_view,
                round_index=round_index,
                previous_execution=prior_execution,
            )
        )
        authorization = (
            round_bundle.authorize_v075_adaptive_round_bundle_v1(frontier)
        )
        if (
            authorization.status
            is not round_bundle.V075BundleAuthorizationStatusV1.AUTHORIZED
        ):
            rounds.append(
                V075IntegratedAdaptiveRoundV1(
                    _ISSUER,
                    round_index,
                    current_backend,
                    current_planner,
                    frontier,
                    authorization,
                    (),
                    None,
                    None,
                    None,
                )
            )
            break
        appended = _execute_round_intents(
            controller=controller,
            namespace=namespace,
            prior_result=current_backend,
            authorization=authorization,
        )
        _require_open_binding(
            controller=controller,
            occurrence_identity=occurrence_identity,
            namespace=namespace,
            context=context,
            arm=arm,
            cap_profile=caps,
        )
        resulting_backend, resulting_planner = _compile_and_plan(
            occurrence_identity=occurrence_identity,
            controller=controller,
            arm=arm,
            occurrence_ordinal=occurrence_ordinal,
            source_prior_transport=source_prior_transport,
        )
        execution = (
            round_bundle.verify_v075_adaptive_round_bundle_execution_v1(
                authorization=authorization,
                resulting_batch_result=resulting_backend,
            )
        )
        if execution.appended_batch_ids != appended:
            _fail("lifecycle append registry differs from bundle replay")
        rounds.append(
            V075IntegratedAdaptiveRoundV1(
                _ISSUER,
                round_index,
                current_backend,
                current_planner,
                frontier,
                authorization,
                appended,
                execution,
                resulting_backend,
                resulting_planner,
            )
        )
        prior_execution = execution
        current_backend = resulting_backend
        current_planner = resulting_planner

    terminal = _terminal_from_state(
        planner_result=current_planner,
        rounds=tuple(rounds),
    )
    if terminal is None:
        _fail("integrated pipeline exited without a registered terminal")
    events = controller.events
    counters = _freeze_counters(
        final_backend=current_backend,
        rounds=tuple(rounds),
        events=events,
    )
    return V075IntegratedOccurrencePrecloseResultV1(
        _ISSUER,
        open_binding,
        occurrence_identity,
        source_view,
        schedule,
        initial_backend,
        initial_planner,
        tuple(rounds),
        current_backend,
        current_planner,
        events,
        counters,
        terminal,
    )


def verify_v075_integrated_occurrence_preclose_result_v1(
    claimed: V075IntegratedOccurrencePrecloseResultV1,
) -> V075IntegratedOccurrenceVerificationV1:
    """Replay every public backend, planner, frontier, and append obligation."""

    if type(claimed) is not V075IntegratedOccurrencePrecloseResultV1:
        _fail("integrated verifier rejects duck-typed results")
    initial_backend = (
        backend.compile_v075_batch_native_statistical_backend_v1(
            claimed.initial_backend_result.request
        )
    )
    initial_planner = backend.plan_v075_batch_native_route_v1(
        initial_backend
    )
    if (
        initial_backend != claimed.initial_backend_result
        or initial_planner != claimed.initial_planner_result
    ):
        _fail("initial backend/planner differs from exact public replay")
    current_backend = initial_backend
    current_planner = initial_planner
    prior_execution = None
    for item in claimed.rounds:
        frontier = (
            round_bundle.freeze_v075_adaptive_round_bundle_frontier_v1(
                batch_result=current_backend,
                planner_result=current_planner,
                source_view=claimed.source_view,
                round_index=item.round_index,
                previous_execution=prior_execution,
            )
        )
        authorization = (
            round_bundle.authorize_v075_adaptive_round_bundle_v1(frontier)
        )
        if (
            frontier != item.frontier
            or authorization != item.authorization
        ):
            _fail("adaptive frontier/authorization differs from exact replay")
        if item.resulting_backend_result is None:
            continue
        resulting_backend = (
            backend.compile_v075_batch_native_statistical_backend_v1(
                item.resulting_backend_result.request
            )
        )
        resulting_planner = backend.plan_v075_batch_native_route_v1(
            resulting_backend
        )
        execution = (
            round_bundle.verify_v075_adaptive_round_bundle_execution_v1(
                authorization=authorization,
                resulting_batch_result=resulting_backend,
            )
        )
        if (
            resulting_backend != item.resulting_backend_result
            or resulting_planner != item.resulting_planner_result
            or execution != item.execution
        ):
            _fail("adaptive execution/backend/planner differs from replay")
        current_backend = resulting_backend
        current_planner = resulting_planner
        prior_execution = execution
    counters = _freeze_counters(
        final_backend=current_backend,
        rounds=claimed.rounds,
        events=claimed.lifecycle_events,
    )
    if (
        current_backend != claimed.final_backend_result
        or current_planner != claimed.final_planner_result
        or counters != claimed.counters
    ):
        _fail("integrated final result or counters differ from exact replay")
    return V075IntegratedOccurrenceVerificationV1(
        claimed.result_id,
        claimed.occurrence_identity.occurrence_id,
        current_backend.result_id,
        current_planner.result_id,
        claimed.terminal_code,
        len(claimed.rounds),
    )


__all__ = [
    "DOMAIN_TAGS",
    "MAX_ADAPTIVE_ROUNDS",
    "MAX_INCREMENTAL_DRAWS",
    "MAX_NEW_CHILD_ACTION_ROWS",
    "PROFILE_KEY",
    "PRODUCTION_INTEGRATION_READY",
    "PROPOSED_CONTRACT_VERSION",
    "SCHEMA_VERSION",
    "V075IntegratedAdaptiveRoundV1",
    "V075IntegratedOccurrenceCountersV1",
    "V075IntegratedOccurrencePipelineInvariantViolation",
    "V075IntegratedOccurrencePrecloseResultV1",
    "V075IntegratedOccurrenceTerminalCodeV1",
    "V075IntegratedOccurrenceVerificationV1",
    "run_v075_integrated_adaptive_occurrence_pipeline_v1",
    "verify_v075_integrated_occurrence_preclose_result_v1",
]
