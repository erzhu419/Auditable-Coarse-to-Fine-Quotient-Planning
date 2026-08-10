"""One-round integrated successor for the batched causal acquisition operator.

This additive pipeline keeps the frozen V1 single-candidate occurrence as its
matched control.  It executes the same registered cold root schedule, freezes
the same failed V1 proof frontier, applies the cap-aware batched authorization,
and recompiles/replans exactly once.  The result remains pre-close: even a
planner candidate is only ready for the existing exact-total-lift authority.

No process isolation, network access, ground oracle, hidden-law callback,
terminal certificate, K7 counter record, or official Gate is exposed here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import hashlib
from typing import Any, Mapping, NoReturn

from acfqp.phase3e_ids import canonical_json_bytes, parse_content_id
from acfqp import v075_adaptive_acquisition_proposal_authority_v1 as proposal
from acfqp import v075_adaptive_acquisition_round_bundle_authority_v1 as v1_bundle
from acfqp import v075_batch_native_statistical_backend_v1 as backend
from acfqp import v075_batched_causal_acquisition_operator_v1 as operator
from acfqp import v075_batched_observer_authority_v1 as batched
from acfqp import v075_learned_support_quotient_planners_v1 as planners
from acfqp import v075_multistage_observer_lifecycle_v1 as lifecycle
from acfqp import v075_public_campaign_authority_v1 as public_authority
from acfqp import v075_public_graph_semantics_v1 as graph
from acfqp import v075_registered_occurrence_worker_v1 as worker


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "1.41.0"
PROFILE_KEY = "v075_batched_causal_occurrence_successor_v1"
PRODUCTION_INTEGRATION_READY = False

_ISSUER = object()

DOMAIN_TAGS = {
    "counters": "acfqp:v075-batched-causal-occurrence-counters:v1",
    "result": "acfqp:v075-batched-causal-occurrence-preclose-result:v1",
    "verification": "acfqp:v075-batched-causal-occurrence-verification:v1",
}
if len(DOMAIN_TAGS) != len(set(DOMAIN_TAGS.values())):  # pragma: no cover
    raise RuntimeError("batched causal occurrence domains must be unique")


class V075BatchedCausalOccurrenceInvariantViolation(ValueError):
    """An occurrence, lifecycle, authorization, or public replay changed."""


def _fail(message: str) -> NoReturn:
    raise V075BatchedCausalOccurrenceInvariantViolation(message)


def _hash(role: str, payload: Mapping[str, Any]) -> str:
    try:
        return hashlib.sha256(
            DOMAIN_TAGS[role].encode("utf-8")
            + b"\x00"
            + canonical_json_bytes(dict(payload))
        ).hexdigest()
    except (KeyError, TypeError, ValueError) as error:
        raise V075BatchedCausalOccurrenceInvariantViolation(str(error)) from error


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise V075BatchedCausalOccurrenceInvariantViolation(
            f"{label} must be one lowercase SHA-256 content ID"
        ) from error


class V075BatchedCausalOccurrenceOutcomeV1(str, Enum):
    CANDIDATE_READY_FOR_EXACT_TOTAL_LIFT = "CANDIDATE_READY_FOR_EXACT_TOTAL_LIFT"
    BATCHED_OPERATOR_NOT_CERTIFIED = "BATCHED_OPERATOR_NOT_CERTIFIED"
    NO_UNCERTAIN_PROOF_FRONTIER = "NO_UNCERTAIN_PROOF_FRONTIER"
    INCREMENTAL_CAP_EXHAUSTED = "INCREMENTAL_CAP_EXHAUSTED"
    PLANNER_SEARCH_CAP_EXHAUSTED = "PLANNER_SEARCH_CAP_EXHAUSTED"


def _bootstrap_stream(
    *,
    namespace: public_authority.V075PublicTargetTapeNamespaceV1,
    row_binding: graph.V075ObservationRowBindingV1,
    arm: worker.V075WorkerArmV1,
) -> tuple[graph.V075SharedSupportEpochV1, graph.V075TransitionStreamIdentityV1]:
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
    return root_epoch, graph.derive_transition_stream_identity_v1(
        pairing_authority=pairing,
        arm=arm.value,
    )


def _support_outcome_ids(
    discovery: batched.V075SignedBatchedObservationV1,
) -> tuple[str, ...]:
    if (
        type(discovery) is not batched.V075SignedBatchedObservationV1
        or discovery.request.stream_identity.lane
        is not graph.V075ObservationLaneV1.DISCOVERY
    ):
        _fail("support selection requires one exact discovery batch")
    row = discovery.request.stream_identity.row_binding
    selected: dict[str, str] = {}
    for outcome in discovery.outcomes:
        state = graph.V075SymbolicGraphStateV1(
            row.context,
            outcome.next_ranks,
            outcome.failure,
        )
        prior = selected.get(state.state_id)
        if prior is None or outcome.outcome_id < prior:
            selected[state.state_id] = outcome.outcome_id
    result = tuple(sorted(selected.values()))
    if not result:
        _fail("discovery exposed no symbolic support")
    return result


def _validation_stream(
    *,
    namespace: public_authority.V075PublicTargetTapeNamespaceV1,
    row_binding: graph.V075ObservationRowBindingV1,
    root_epoch: graph.V075SharedSupportEpochV1,
    evidence: tuple[graph.V075BatchAggregateSupportEvidenceV1, ...],
    arm: worker.V075WorkerArmV1,
) -> graph.V075TransitionStreamIdentityV1:
    epoch = graph.derive_shared_support_epoch_v1(
        namespace=namespace,
        row_binding=row_binding,
        epoch_index=1,
        evidence=evidence,
        parent=root_epoch,
    )
    chain = graph.freeze_shared_support_chain_v1(
        namespace=namespace,
        row_binding=row_binding,
        epochs=(root_epoch, epoch),
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
    if type(controller) is not lifecycle.V075ParentOwnedMultistageObserverLifecycleV1:
        _fail("batched successor requires one exact parent-owned lifecycle")
    binding = controller.open_binding
    if (
        type(binding) is not lifecycle.V075OpenMultistageLifecycleBindingV1
        or binding.occurrence_id != occurrence_identity.occurrence_id
        or binding.context_id != context.context_id
        or binding.arm is not arm
        or binding.route_cap_profile != cap_profile
        or binding.namespace != namespace
        or binding.target_tape_namespace_id
        != occurrence_identity.target_tape_namespace_id
        or binding.route_cap_profile_id != occurrence_identity.cap_profile_id
    ):
        _fail("open lifecycle differs from the frozen occurrence")
    return binding


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
    observed: dict[
        str,
        tuple[graph.V075SharedSupportEpochV1, batched.V075SignedBatchedObservationV1],
    ] = {}
    streams: dict[str, graph.V075TransitionStreamIdentityV1] = {}
    for intent in discoveries:
        root, stream = _bootstrap_stream(
            namespace=namespace,
            row_binding=intent.row_binding,
            arm=schedule.arm,
        )
        batch = controller.execute_batch_v1(
            stream_identity=stream,
            accepted_draw_start=intent.accepted_draw_start,
            accepted_draw_count=intent.accepted_draw_count,
            accepted_draw_cap=intent.accepted_draw_cap,
        )
        observed[intent.intent_id] = (root, batch)
    for intent in validations:
        dependency = observed.get(intent.dependency_intent_id)
        if dependency is None:
            _fail("root validation dependency was reordered")
        root, discovery = dependency
        evidence = controller.freeze_aggregate_support_evidence_v1(
            discovery_batch=discovery,
            selected_outcome_ids=_support_outcome_ids(discovery),
        )
        stream = _validation_stream(
            namespace=namespace,
            row_binding=intent.row_binding,
            root_epoch=root,
            evidence=evidence,
            arm=schedule.arm,
        )
        controller.register_validation_support_epoch_v1(stream_identity=stream)
        streams[intent.intent_id] = stream
    for intent in validations:
        controller.execute_batch_v1(
            stream_identity=streams[intent.intent_id],
            accepted_draw_start=intent.accepted_draw_start,
            accepted_draw_count=intent.accepted_draw_count,
            accepted_draw_cap=intent.accepted_draw_cap,
        )


def _compile_and_plan(
    *,
    occurrence_identity: backend.V075BatchNativeOccurrenceIdentityV1,
    controller: lifecycle.V075ParentOwnedMultistageObserverLifecycleV1,
    arm: worker.V075WorkerArmV1,
    occurrence_ordinal: int,
    source_prior_transport: worker.V075SourcePriorTransportV1 | None,
) -> tuple[backend.V075BatchNativeBackendResultV1, planners.V075SupportPlannerResultV1]:
    request = backend.freeze_v075_batch_native_backend_request_v1(
        arm=arm,
        occurrence_ordinal=occurrence_ordinal,
        batches=controller.batches,
        source_prior_transport=source_prior_transport,
        occurrence_identity=occurrence_identity,
    )
    result = backend.compile_v075_batch_native_statistical_backend_v1(request)
    return result, backend.plan_v075_batch_native_route_v1(result)


def _execute_authorization(
    *,
    controller: lifecycle.V075ParentOwnedMultistageObserverLifecycleV1,
    namespace: public_authority.V075PublicTargetTapeNamespaceV1,
    prior_result: backend.V075BatchNativeBackendResultV1,
    authorization: operator.V075BatchedCausalAcquisitionAuthorizationV1,
) -> tuple[str, ...]:
    if (
        authorization.outcome
        is not operator.V075BatchedCausalAuthorizationOutcomeV1.AUTHORIZED
    ):
        _fail("observer execution requires one authorized batched union")
    controller.start_adaptive_round_v1(authorization.frontier.round_index)
    before = {item.batch_id for item in controller.batches}
    discoveries: dict[
        str,
        tuple[graph.V075SharedSupportEpochV1, batched.V075SignedBatchedObservationV1],
    ] = {}
    validation_streams: dict[str, graph.V075TransitionStreamIdentityV1] = {}
    for intent in authorization.intents:
        if intent.kind is not operator.V075BatchedCausalIntentKindV1.NEW_CHILD_ROW_DISCOVERY:
            continue
        root, stream = _bootstrap_stream(
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
        discoveries[intent.intent_id] = (root, observed)
    for intent in authorization.intents:
        if intent.kind is not operator.V075BatchedCausalIntentKindV1.NEW_CHILD_ROW_VALIDATION:
            continue
        dependency = discoveries.get(intent.dependency_intent_id)
        if dependency is None:
            _fail("batched validation lacks its exact discovery")
        root, discovery = dependency
        evidence = controller.freeze_aggregate_support_evidence_v1(
            discovery_batch=discovery,
            selected_outcome_ids=_support_outcome_ids(discovery),
        )
        stream = _validation_stream(
            namespace=namespace,
            row_binding=intent.row_binding,
            root_epoch=root,
            evidence=evidence,
            arm=authorization.frontier.arm,
        )
        controller.register_validation_support_epoch_v1(stream_identity=stream)
        validation_streams[intent.intent_id] = stream
    existing = {
        item.request.stream_identity.stream_id: item.request.stream_identity
        for item in prior_result.request.batches
    }
    for intent in authorization.intents:
        if intent.kind is operator.V075BatchedCausalIntentKindV1.NEW_CHILD_ROW_DISCOVERY:
            continue
        if intent.kind is operator.V075BatchedCausalIntentKindV1.EXISTING_VALIDATION_PREFIX_EXTENSION:
            stream = existing.get(intent.existing_stream_id)
            if stream is None:
                _fail("batched promotion stream was transplanted")
        else:
            stream = validation_streams.get(intent.intent_id)
            if stream is None:
                _fail("batched child validation stream was not registered")
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
        _fail("authorized batched union appended no observations")
    return appended


@dataclass(frozen=True, slots=True)
class V075BatchedCausalOccurrenceCountersV1:
    _issuer: object = field(repr=False, compare=False)
    final_backend_result_id: str
    accepted_draws: int
    cold_root_draws: int
    incremental_draws: int
    observer_batches: int
    lifecycle_events: int
    child_action_rows_materialized: int
    selected_causal_candidates: int
    backend_compilations: int = 2
    planner_invocations: int = 2
    process_launches: int = 0

    def __post_init__(self) -> None:
        _cid(self.final_backend_result_id, "batched counter backend")
        values = (
            self.accepted_draws,
            self.cold_root_draws,
            self.incremental_draws,
            self.observer_batches,
            self.lifecycle_events,
            self.child_action_rows_materialized,
            self.selected_causal_candidates,
            self.backend_compilations,
            self.planner_invocations,
            self.process_launches,
        )
        caps = worker.V075WorkerCapProfileV1()
        if (
            self._issuer is not _ISSUER
            or any(type(value) is not int or value < 0 for value in values)
            or self.accepted_draws != self.cold_root_draws + self.incremental_draws
            or self.incremental_draws > caps.maximum_incremental_draws_per_adaptive_arm
            or self.child_action_rows_materialized > caps.maximum_new_child_action_rows
            or self.selected_causal_candidates <= 1
            or self.backend_compilations != 2
            or self.planner_invocations != 2
            or self.process_launches != 0
        ):
            _fail("batched occurrence counters are inconsistent")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_batched_causal_occurrence_counters.v1",
            "schema_version": SCHEMA_VERSION,
            "final_backend_result_id": self.final_backend_result_id,
            "accepted_draws": self.accepted_draws,
            "cold_root_draws": self.cold_root_draws,
            "incremental_draws": self.incremental_draws,
            "observer_batches": self.observer_batches,
            "lifecycle_events": self.lifecycle_events,
            "child_action_rows_materialized": self.child_action_rows_materialized,
            "selected_causal_candidates": self.selected_causal_candidates,
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


def _preclose_outcome(
    *,
    planner: planners.V075SupportPlannerResultV1,
    authorization: operator.V075BatchedCausalAcquisitionAuthorizationV1,
) -> V075BatchedCausalOccurrenceOutcomeV1:
    if planner.ready_for_exact_total_lift:
        return V075BatchedCausalOccurrenceOutcomeV1.CANDIDATE_READY_FOR_EXACT_TOTAL_LIFT
    if planner.status is planners.V075PlannerStatusV1.SEARCH_CAP_EXHAUSTED:
        return V075BatchedCausalOccurrenceOutcomeV1.PLANNER_SEARCH_CAP_EXHAUSTED
    if authorization.outcome is operator.V075BatchedCausalAuthorizationOutcomeV1.NO_UNCERTAIN_PROOF_FRONTIER:
        return V075BatchedCausalOccurrenceOutcomeV1.NO_UNCERTAIN_PROOF_FRONTIER
    if authorization.outcome is operator.V075BatchedCausalAuthorizationOutcomeV1.INCREMENTAL_CAP_EXHAUSTED:
        return V075BatchedCausalOccurrenceOutcomeV1.INCREMENTAL_CAP_EXHAUSTED
    return V075BatchedCausalOccurrenceOutcomeV1.BATCHED_OPERATOR_NOT_CERTIFIED


@dataclass(frozen=True, slots=True)
class V075BatchedCausalOccurrencePrecloseResultV1:
    _issuer: object = field(repr=False, compare=False)
    open_lifecycle_binding: lifecycle.V075OpenMultistageLifecycleBindingV1
    occurrence_identity: backend.V075BatchNativeOccurrenceIdentityV1
    source_view: proposal.V075SourceProposalViewV1
    initial_schedule: proposal.V075InitialRootAcquisitionScheduleV1
    initial_backend_result: backend.V075BatchNativeBackendResultV1
    initial_planner_result: planners.V075SupportPlannerResultV1
    frontier: v1_bundle.V075AdaptiveRoundBundleFrontierV1
    authorization: operator.V075BatchedCausalAcquisitionAuthorizationV1
    appended_batch_ids: tuple[str, ...]
    execution: operator.V075BatchedCausalAcquisitionExecutionV1
    final_backend_result: backend.V075BatchNativeBackendResultV1
    final_planner_result: planners.V075SupportPlannerResultV1
    lifecycle_events: tuple[lifecycle.V075MultistageLifecycleEventV1, ...]
    counters: V075BatchedCausalOccurrenceCountersV1
    outcome: V075BatchedCausalOccurrenceOutcomeV1

    def __post_init__(self) -> None:
        if (
            self._issuer is not _ISSUER
            or type(self.open_lifecycle_binding) is not lifecycle.V075OpenMultistageLifecycleBindingV1
            or type(self.occurrence_identity) is not backend.V075BatchNativeOccurrenceIdentityV1
            or type(self.source_view) is not proposal.V075SourceProposalViewV1
            or type(self.initial_schedule) is not proposal.V075InitialRootAcquisitionScheduleV1
            or type(self.initial_backend_result) is not backend.V075BatchNativeBackendResultV1
            or type(self.initial_planner_result) is not planners.V075SupportPlannerResultV1
            or type(self.frontier) is not v1_bundle.V075AdaptiveRoundBundleFrontierV1
            or type(self.authorization) is not operator.V075BatchedCausalAcquisitionAuthorizationV1
            or type(self.execution) is not operator.V075BatchedCausalAcquisitionExecutionV1
            or type(self.final_backend_result) is not backend.V075BatchNativeBackendResultV1
            or type(self.final_planner_result) is not planners.V075SupportPlannerResultV1
            or type(self.counters) is not V075BatchedCausalOccurrenceCountersV1
            or type(self.outcome) is not V075BatchedCausalOccurrenceOutcomeV1
        ):
            _fail("batched causal preclose result is untyped")
        if (
            self.open_lifecycle_binding.occurrence_id != self.occurrence_identity.occurrence_id
            or self.initial_backend_result.request.occurrence_identity != self.occurrence_identity
            or self.initial_planner_result.graph.backend_result
            != self.initial_backend_result.route_native_result
            or self.frontier.batch_result_id != self.initial_backend_result.result_id
            or self.frontier.planner_result_id != self.initial_planner_result.result_id
            or self.authorization.frontier != self.frontier
            or self.execution.authorization_id != self.authorization.authorization_id
            or self.execution.prior_batch_result_id != self.initial_backend_result.result_id
            or self.execution.resulting_batch_result_id != self.final_backend_result.result_id
            or self.appended_batch_ids != self.execution.appended_batch_ids
            or self.final_planner_result.graph.backend_result
            != self.final_backend_result.route_native_result
            or self.counters.final_backend_result_id != self.final_backend_result.result_id
            or self.outcome
            is not _preclose_outcome(
                planner=self.final_planner_result,
                authorization=self.authorization,
            )
        ):
            _fail("batched causal result identity graph or preclose outcome changed")
        event_ids = tuple(item.event_id for item in self.lifecycle_events)
        if (
            tuple(item.sequence_number for item in self.lifecycle_events)
            != tuple(range(1, len(self.lifecycle_events) + 1))
            or len(set(event_ids)) != len(event_ids)
            or {item.batch_id for item in self.lifecycle_events if item.batch_id is not None}
            != {item.batch_id for item in self.final_backend_result.request.batches}
        ):
            _fail("batched causal lifecycle registry is incomplete")

    @property
    def ready_for_exact_total_lift(self) -> bool:
        return self.outcome is V075BatchedCausalOccurrenceOutcomeV1.CANDIDATE_READY_FOR_EXACT_TOTAL_LIFT

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_batched_causal_occurrence_preclose_result.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "open_lifecycle_binding_id": self.open_lifecycle_binding.binding_id,
            "occurrence_identity_id": self.occurrence_identity.occurrence_id,
            "source_view_id": self.source_view.source_view_id,
            "initial_schedule_id": self.initial_schedule.schedule_id,
            "initial_backend_result_id": self.initial_backend_result.result_id,
            "initial_planner_result_id": self.initial_planner_result.result_id,
            "frontier_id": self.frontier.frontier_id,
            "authorization_id": self.authorization.authorization_id,
            "execution_id": self.execution.execution_id,
            "appended_batch_ids": list(self.appended_batch_ids),
            "final_backend_result_id": self.final_backend_result.result_id,
            "final_planner_result_id": self.final_planner_result.result_id,
            "lifecycle_event_ids": [item.event_id for item in self.lifecycle_events],
            "counters_id": self.counters.counters_id,
            "preclose_outcome": self.outcome.value,
            "ready_for_exact_total_lift": self.ready_for_exact_total_lift,
            "artifact_scope": "PRE_CLOSE_OPERATIONAL_INTERMEDIATE",
            "scientific_plan_certificate": False,
            "occurrence_closed": False,
            "production_integration_ready": False,
            "k7_counter_records_issued": 0,
        }

    @property
    def result_id(self) -> str:
        return _hash("result", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "open_lifecycle_binding": self.open_lifecycle_binding.to_document(),
            "occurrence_identity": self.occurrence_identity.to_document(),
            "source_view": self.source_view.to_document(),
            "initial_schedule": self.initial_schedule.to_document(),
            "frontier": self.frontier.to_document(),
            "authorization": self.authorization.to_document(),
            "execution": self.execution.to_document(),
            "counters": self.counters.to_document(),
            "result_id": self.result_id,
        }


@dataclass(frozen=True, slots=True)
class V075BatchedCausalOccurrenceVerificationV1:
    result_id: str
    occurrence_id: str
    final_backend_result_id: str
    final_planner_result_id: str
    outcome: V075BatchedCausalOccurrenceOutcomeV1

    def __post_init__(self) -> None:
        for value, label in (
            (self.result_id, "verified result"),
            (self.occurrence_id, "verified occurrence"),
            (self.final_backend_result_id, "verified backend"),
            (self.final_planner_result_id, "verified planner"),
        ):
            _cid(value, label)
        if type(self.outcome) is not V075BatchedCausalOccurrenceOutcomeV1:
            _fail("batched causal verification outcome is invalid")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_batched_causal_occurrence_verification.v1",
            "schema_version": SCHEMA_VERSION,
            "result_id": self.result_id,
            "occurrence_id": self.occurrence_id,
            "final_backend_result_id": self.final_backend_result_id,
            "final_planner_result_id": self.final_planner_result_id,
            "preclose_outcome": self.outcome.value,
            "exact_public_semantic_replay": True,
        }

    @property
    def verification_id(self) -> str:
        return _hash("verification", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "verification_id": self.verification_id}


def _freeze_counters(
    *,
    initial_backend: backend.V075BatchNativeBackendResultV1,
    final_backend: backend.V075BatchNativeBackendResultV1,
    authorization: operator.V075BatchedCausalAcquisitionAuthorizationV1,
    events: tuple[lifecycle.V075MultistageLifecycleEventV1, ...],
) -> V075BatchedCausalOccurrenceCountersV1:
    initial_accounting = v1_bundle.replay_v075_incremental_accounting_v1(initial_backend)
    final_accounting = v1_bundle.replay_v075_incremental_accounting_v1(final_backend)
    accepted = sum(
        item.request.accepted_draw_count for item in final_backend.request.batches
    )
    return V075BatchedCausalOccurrenceCountersV1(
        _ISSUER,
        final_backend.result_id,
        accepted,
        accepted - final_accounting.incremental_draws_used,
        final_accounting.incremental_draws_used,
        len(final_backend.request.batches),
        len(events),
        len(final_accounting.new_child_action_row_ids),
        len(authorization.selected_candidate_ids),
    )


def run_v075_batched_causal_occurrence_successor_v1(
    *,
    controller: lifecycle.V075ParentOwnedMultistageObserverLifecycleV1,
    namespace: public_authority.V075PublicTargetTapeNamespaceV1,
    context: public_authority.V075PublicReplicateContextV1,
    arm: worker.V075WorkerArmV1,
    occurrence_ordinal: int,
    source_prior_transport: worker.V075SourcePriorTransportV1 | None = None,
) -> V075BatchedCausalOccurrencePrecloseResultV1:
    """Execute one preregistered cap-aware batched acquisition round."""

    if (
        type(namespace) is not public_authority.V075PublicTargetTapeNamespaceV1
        or type(context) is not public_authority.V075PublicReplicateContextV1
        or context not in namespace.family.replicate_contexts
        or type(arm) is not worker.V075WorkerArmV1
        or arm is worker.V075WorkerArmV1.MATCHED_DIRECT_GROUND
        or type(occurrence_ordinal) is not int
        or occurrence_ordinal < 0
        or (source_prior_transport is not None)
        != (arm is worker.V075WorkerArmV1.SOURCE_CONSENSUS_PRIOR)
    ):
        _fail("batched causal occurrence inputs are invalid")
    if controller.batches or controller.events:
        _fail("batched causal successor requires an unused lifecycle")
    caps = worker.V075WorkerCapProfileV1()
    identity = backend.freeze_v075_batch_native_occurrence_identity_v1(
        namespace=namespace,
        context=context,
        arm=arm,
        occurrence_ordinal=occurrence_ordinal,
        threshold_profile=worker.V075WorkerThresholdProfileV1(),
        cap_profile=caps,
        source_prior_transport=source_prior_transport,
    )
    binding = _require_open_binding(
        controller=controller,
        occurrence_identity=identity,
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
    _execute_initial_schedule(controller=controller, namespace=namespace, schedule=schedule)
    initial_backend, initial_planner = _compile_and_plan(
        occurrence_identity=identity,
        controller=controller,
        arm=arm,
        occurrence_ordinal=occurrence_ordinal,
        source_prior_transport=source_prior_transport,
    )
    frontier = v1_bundle.freeze_v075_adaptive_round_bundle_frontier_v1(
        batch_result=initial_backend,
        planner_result=initial_planner,
        source_view=source_view,
        round_index=1,
    )
    authorization = operator.authorize_v075_batched_causal_acquisition_v1(frontier)
    if authorization.outcome is not operator.V075BatchedCausalAuthorizationOutcomeV1.AUTHORIZED:
        _fail("registered deterministic successor requires an authorized batched frontier")
    appended = _execute_authorization(
        controller=controller,
        namespace=namespace,
        prior_result=initial_backend,
        authorization=authorization,
    )
    _require_open_binding(
        controller=controller,
        occurrence_identity=identity,
        namespace=namespace,
        context=context,
        arm=arm,
        cap_profile=caps,
    )
    final_backend, final_planner = _compile_and_plan(
        occurrence_identity=identity,
        controller=controller,
        arm=arm,
        occurrence_ordinal=occurrence_ordinal,
        source_prior_transport=source_prior_transport,
    )
    execution = operator.verify_v075_batched_causal_acquisition_execution_v1(
        authorization=authorization,
        resulting_batch_result=final_backend,
    )
    if execution.appended_batch_ids != appended:
        _fail("lifecycle append registry differs from operator replay")
    events = controller.events
    counters = _freeze_counters(
        initial_backend=initial_backend,
        final_backend=final_backend,
        authorization=authorization,
        events=events,
    )
    return V075BatchedCausalOccurrencePrecloseResultV1(
        _ISSUER,
        binding,
        identity,
        source_view,
        schedule,
        initial_backend,
        initial_planner,
        frontier,
        authorization,
        appended,
        execution,
        final_backend,
        final_planner,
        events,
        counters,
        _preclose_outcome(planner=final_planner, authorization=authorization),
    )


def verify_v075_batched_causal_occurrence_successor_v1(
    claimed: V075BatchedCausalOccurrencePrecloseResultV1,
) -> V075BatchedCausalOccurrenceVerificationV1:
    """Replay public backend, planner, frontier, union, and exact append."""

    if type(claimed) is not V075BatchedCausalOccurrencePrecloseResultV1:
        _fail("batched causal verifier rejects duck-typed results")
    initial_backend = backend.compile_v075_batch_native_statistical_backend_v1(
        claimed.initial_backend_result.request
    )
    initial_planner = backend.plan_v075_batch_native_route_v1(initial_backend)
    frontier = v1_bundle.freeze_v075_adaptive_round_bundle_frontier_v1(
        batch_result=initial_backend,
        planner_result=initial_planner,
        source_view=claimed.source_view,
        round_index=1,
    )
    authorization = operator.authorize_v075_batched_causal_acquisition_v1(frontier)
    final_backend = backend.compile_v075_batch_native_statistical_backend_v1(
        claimed.final_backend_result.request
    )
    final_planner = backend.plan_v075_batch_native_route_v1(final_backend)
    execution = operator.verify_v075_batched_causal_acquisition_execution_v1(
        authorization=authorization,
        resulting_batch_result=final_backend,
    )
    counters = _freeze_counters(
        initial_backend=initial_backend,
        final_backend=final_backend,
        authorization=authorization,
        events=claimed.lifecycle_events,
    )
    if (
        initial_backend != claimed.initial_backend_result
        or initial_planner != claimed.initial_planner_result
        or frontier != claimed.frontier
        or authorization != claimed.authorization
        or final_backend != claimed.final_backend_result
        or final_planner != claimed.final_planner_result
        or execution != claimed.execution
        or counters != claimed.counters
    ):
        _fail("batched causal successor differs from exact public replay")
    return V075BatchedCausalOccurrenceVerificationV1(
        claimed.result_id,
        claimed.occurrence_identity.occurrence_id,
        final_backend.result_id,
        final_planner.result_id,
        claimed.outcome,
    )


__all__ = [
    "PROFILE_KEY",
    "PRODUCTION_INTEGRATION_READY",
    "V075BatchedCausalOccurrenceCountersV1",
    "V075BatchedCausalOccurrenceInvariantViolation",
    "V075BatchedCausalOccurrencePrecloseResultV1",
    "V075BatchedCausalOccurrenceOutcomeV1",
    "V075BatchedCausalOccurrenceVerificationV1",
    "run_v075_batched_causal_occurrence_successor_v1",
    "verify_v075_batched_causal_occurrence_successor_v1",
]
