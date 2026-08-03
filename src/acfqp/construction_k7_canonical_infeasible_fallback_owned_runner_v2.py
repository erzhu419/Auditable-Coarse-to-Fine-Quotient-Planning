"""Authorized canonical H1 runner for the production-owned fallback slice.

The durable/current identity, exact cardinality, upper and marginal FALLBACK
decision are frozen before the first route ground transition.  Execution then
uses the copied V2 search under an exact V3 owner-bound accounting session.

This construction runner intentionally stops at a verified positive-event
route segment.  It does not issue the remaining shared-resource receipts,
native zeros, derived rows, V6 CounterRecords, vectors, or an FQ9 terminal.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
import hashlib
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_canonical_infeasible_fallback_acquisition_v1 as acquisition_v1
from acfqp import construction_k7_direct_fallback_operation_boundary_manifest_v3 as manifest_v3
from acfqp import phase3e_fallback_owned_v2 as owned_v2
from acfqp.accounting_v1 import official_counter_registry_v1
from acfqp.construction_accounting_route_segment_v3 import (
    OwnedFallbackRouteSegmentSessionV3,
    OwnedRouteSegmentTranscriptV3,
    RouteSegmentTerminalKindV3,
    activate_owned_route_segment_v3,
)
from acfqp.domains.g2048 import G2048Kernel
from acfqp.phase3e_fallback_owned_v2 import run_owned_ground_fallback_search_v2
from acfqp.phase3e_fallback_v1 import (
    GroundFallbackCapProfileV1,
    GroundFallbackExecutionV1,
    GroundFallbackOutcome,
)
from acfqp.phase3e_ids import canonical_json_bytes, parse_content_id
from acfqp.routing_v1 import RouteSelection


SCHEMA_VERSION = "2.0.0"
PROFILE_KEY = "construction_k7_canonical_infeasible_fallback_owned_runner_v2"
CONSTRUCTION_ONLY = True
OFFICIAL_EXECUTION_ALLOWED = False
PRODUCTION_OWNER_SOURCE_INTEGRATED = True
COMPLETE_ACCOUNTING_CHAIN_ISSUED = False
TERMINAL_ARTIFACT_ISSUED = False

EXPECTED_VALUES = {
    "fallback.states_expanded": 8,
    "fallback.actions_evaluated": 16,
    "fallback.ground_steps": 16,
    "fallback.outcome_rows": 96,
    "fallback.bellman_backups": 16,
    "control.cap_checks": 56,
    "control.cap_rejections": 0,
}
EXPECTED_EVENT_COUNT = 208

_RESULT_DOMAIN = "acfqp:construction-k7-owned-fallback-runner-result:v2"
_SUPPORT_DOMAIN = "acfqp:construction-k7-owned-fallback-runner-support:v2"
_ISSUER = object()


class ConstructionK7CanonicalInfeasibleFallbackOwnedRunnerV2Error(ValueError):
    """The authorization, owned transcript, or exact H1 result is invalid."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7CanonicalInfeasibleFallbackOwnedRunnerV2Error(message)


def _content_id(domain: str, payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(
        domain.encode("utf-8") + b"\x00" + canonical_json_bytes(dict(payload))
    ).hexdigest()


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionK7CanonicalInfeasibleFallbackOwnedRunnerV2Error(
            f"{label} must be one full content ID"
        ) from error


@dataclass(frozen=True, slots=True)
class CanonicalOwnedFallbackRunnerResultV2:
    _issuer: InitVar[object]
    proof_bytes_sha256: str
    preexecution: acquisition_v1.CanonicalDirectFallbackPreexecutionCandidateV1
    boundary_manifest_id: str
    source_replay_id: str
    transition_trace_id: str
    execution: GroundFallbackExecutionV1 = field(repr=False, compare=False)
    transcript: OwnedRouteSegmentTranscriptV3
    outcome: str
    _result_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _ISSUER
            or type(self.preexecution)
            is not acquisition_v1.CanonicalDirectFallbackPreexecutionCandidateV1
            or type(self.execution) is not GroundFallbackExecutionV1
            or type(self.transcript) is not OwnedRouteSegmentTranscriptV3
        ):
            _fail("owned fallback runner result is caller-minted")
        if (
            type(self.proof_bytes_sha256) is not str
            or len(self.proof_bytes_sha256) != 64
        ):
            _fail("owned fallback runner proof digest is invalid")
        for value, label in (
            (self.boundary_manifest_id, "boundary manifest"),
            (self.source_replay_id, "source replay"),
            (self.transition_trace_id, "transition trace"),
        ):
            _cid(value, label)
        result = self.execution.result
        values = dict(self.transcript.values)
        if (
            self.outcome != "OWNED_EXACT_INFEASIBILITY_SEGMENT_VERIFIED"
            or self.preexecution.decision.selected_route is not RouteSelection.FALLBACK
            or result.outcome is not GroundFallbackOutcome.INFEASIBLE_CERTIFIED
            or result.search_complete is not True
            or result.frontier == ()
            or result.selected_policy_signature
            or self.execution.selected_policy is not None
            or self.transcript.terminal.terminal_kind
            is not RouteSegmentTerminalKindV3.COMPLETED
            or len(self.transcript.events) != EXPECTED_EVENT_COUNT
            or values
            != {path: value for path, value in EXPECTED_VALUES.items() if value > 0}
            or any(
                self.execution.work_vector.values[path] != value
                for path, value in EXPECTED_VALUES.items()
            )
            or result.route_decision_context_id
            != self.preexecution.route_context.route_decision_context_id
            or result.decision_point_id
            != self.preexecution.decision_point.decision_point_id
            or result.route_decision_id != self.preexecution.decision.route_decision_id
            or result.selected_upper_id
            != self.preexecution.upper.route_upper_bound_envelope_id
            or result.route_attempt_id
            != self.preexecution.route_context.route_attempt_id
        ):
            _fail("owned fallback runner result is not the exact H1 segment")
        object.__setattr__(self, "_result_id", _content_id(_RESULT_DOMAIN, self._payload()))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.canonical_owned_fallback_runner_result.v2",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "proof_bytes_sha256": self.proof_bytes_sha256,
            "preexecution": self.preexecution.to_document(),
            "boundary_manifest_id": self.boundary_manifest_id,
            "source_replay_id": self.source_replay_id,
            "transition_trace_id": self.transition_trace_id,
            "legacy_transport_result": self.execution.result.to_dict(),
            "legacy_transport_work_vector": self.execution.work_vector.to_dict(),
            "owned_route_segment_transcript": self.transcript.to_document(),
            "outcome": self.outcome,
            "selected_route_frozen_before_ground_access": True,
            "exact_expected_values": [
                {"path": path, "value": value}
                for path, value in sorted(EXPECTED_VALUES.items())
            ],
            "exact_event_count": EXPECTED_EVENT_COUNT,
            "production_owner_source_integrated": True,
            "complete_accounting_chain_issued": False,
            "counter_records_issued": 0,
            "work_vectors_v6_issued": 0,
            "comparison_vectors_issued": 0,
            "terminal_artifact_issued": False,
            "official_execution_allowed": False,
            "construction_only": True,
        }

    @property
    def result_id(self) -> str:
        if _content_id(_RESULT_DOMAIN, self._payload()) != self._result_id:
            _fail("owned fallback runner result changed after issuance")
        return self._result_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "owned_fallback_runner_result_id": self.result_id}


_EXPECTED_OWNED_SEARCH = run_owned_ground_fallback_search_v2
_EXPECTED_OWNED_SEARCH_GLOBALS = run_owned_ground_fallback_search_v2.__globals__
_EXPECTED_OWNED_SEARCH_CODE = run_owned_ground_fallback_search_v2.__code__
_EXPECTED_KERNEL_CLASS = G2048Kernel
_EXPECTED_KERNEL_STEP = G2048Kernel.step
_EXPECTED_KERNEL_ACTIONS = G2048Kernel.actions
_EXPECTED_KERNEL_INITIAL = G2048Kernel.initial_distribution
_EXPECTED_PROOF_DOCUMENT = acquisition_v1._proof_document
_EXPECTED_PREEXECUTION = acquisition_v1._preexecution_candidate
_EXPECTED_CANONICAL_QUERY = acquisition_v1._canonical_query
_EXPECTED_INITIAL_LAW_VERIFY = acquisition_v1._verify_initial_law
_EXPECTED_LIVE_EXECUTION_VERIFY = acquisition_v1._verify_live_execution
_EXPECTED_TRACING_KERNEL = acquisition_v1._TracingKernel
_EXPECTED_MANIFEST_LOAD = manifest_v3.load_direct_fallback_operation_source_archive_v3
_EXPECTED_MANIFEST_REPLAY = manifest_v3.replay_direct_fallback_operation_source_archive_v3
_EXPECTED_SESSION_CLASS = OwnedFallbackRouteSegmentSessionV3
_EXPECTED_ACTIVATION = activate_owned_route_segment_v3
_EXPECTED_V1_REGISTRY_FACTORY = official_counter_registry_v1
_EXPECTED_OWNER_BINDING_VALIDATOR = (
    owned_v2.require_frozen_owned_fallback_source_binding_v2
)
_EXPECTED_OWNER_BINDING_VALIDATOR_GLOBALS = (
    _EXPECTED_OWNER_BINDING_VALIDATOR.__globals__
)
_EXPECTED_OWNER_BINDING_VALIDATOR_CODE = (
    _EXPECTED_OWNER_BINDING_VALIDATOR.__code__
)
_EXPECTED_OWNER_BINDING = _EXPECTED_OWNER_BINDING_VALIDATOR()


def _require_live_callables() -> None:
    if (
        owned_v2.require_frozen_owned_fallback_source_binding_v2
        is not _EXPECTED_OWNER_BINDING_VALIDATOR
        or _EXPECTED_OWNER_BINDING_VALIDATOR.__globals__
        is not _EXPECTED_OWNER_BINDING_VALIDATOR_GLOBALS
        or _EXPECTED_OWNER_BINDING_VALIDATOR.__code__
        is not _EXPECTED_OWNER_BINDING_VALIDATOR_CODE
    ):
        _fail("owned fallback import-time binding validator changed")
    try:
        current_owner_binding = _EXPECTED_OWNER_BINDING_VALIDATOR()
    except (AttributeError, TypeError, ValueError) as error:
        raise ConstructionK7CanonicalInfeasibleFallbackOwnedRunnerV2Error(
            "owned fallback import-time class/method binding changed"
        ) from error
    if (
        run_owned_ground_fallback_search_v2 is not _EXPECTED_OWNED_SEARCH
        or run_owned_ground_fallback_search_v2.__globals__
        is not _EXPECTED_OWNED_SEARCH_GLOBALS
        or run_owned_ground_fallback_search_v2.__code__
        is not _EXPECTED_OWNED_SEARCH_CODE
        or owned_v2.run_owned_ground_fallback_search_v2
        is not _EXPECTED_OWNED_SEARCH
        or owned_v2.require_frozen_owned_fallback_source_binding_v2
        is not _EXPECTED_OWNER_BINDING_VALIDATOR
        or current_owner_binding.owner_class is not _EXPECTED_OWNER_BINDING.owner_class
        or current_owner_binding.owner_globals is not _EXPECTED_OWNER_BINDING.owner_globals
        or current_owner_binding.gateway is not _EXPECTED_OWNER_BINDING.gateway
        or current_owner_binding.gateway_globals
        is not _EXPECTED_OWNER_BINDING.gateway_globals
        or current_owner_binding.gateway_code
        is not _EXPECTED_OWNER_BINDING.gateway_code
        or current_owner_binding.event_ack is not _EXPECTED_OWNER_BINDING.event_ack
        or current_owner_binding.search_bind is not _EXPECTED_OWNER_BINDING.search_bind
        or current_owner_binding.search_bind_globals
        is not _EXPECTED_OWNER_BINDING.search_bind_globals
        or current_owner_binding.search_bind_code
        is not _EXPECTED_OWNER_BINDING.search_bind_code
        or current_owner_binding.search_finish
        is not _EXPECTED_OWNER_BINDING.search_finish
        or current_owner_binding.search_finish_globals
        is not _EXPECTED_OWNER_BINDING.search_finish_globals
        or current_owner_binding.search_finish_code
        is not _EXPECTED_OWNER_BINDING.search_finish_code
        or len(current_owner_binding.method_bindings)
        != len(_EXPECTED_OWNER_BINDING.method_bindings)
        or any(
            left_name != right_name
            or left_function is not right_function
            or left_code is not right_code
            for (left_name, left_function, left_code), (
                right_name,
                right_function,
                right_code,
            ) in zip(
                current_owner_binding.method_bindings,
                _EXPECTED_OWNER_BINDING.method_bindings,
            )
        )
        or G2048Kernel is not _EXPECTED_KERNEL_CLASS
        or G2048Kernel.step is not _EXPECTED_KERNEL_STEP
        or G2048Kernel.actions is not _EXPECTED_KERNEL_ACTIONS
        or G2048Kernel.initial_distribution is not _EXPECTED_KERNEL_INITIAL
        or acquisition_v1._proof_document is not _EXPECTED_PROOF_DOCUMENT
        or acquisition_v1._preexecution_candidate is not _EXPECTED_PREEXECUTION
        or acquisition_v1._canonical_query is not _EXPECTED_CANONICAL_QUERY
        or acquisition_v1._verify_initial_law is not _EXPECTED_INITIAL_LAW_VERIFY
        or acquisition_v1._verify_live_execution
        is not _EXPECTED_LIVE_EXECUTION_VERIFY
        or acquisition_v1._TracingKernel is not _EXPECTED_TRACING_KERNEL
        or manifest_v3.load_direct_fallback_operation_source_archive_v3
        is not _EXPECTED_MANIFEST_LOAD
        or manifest_v3.replay_direct_fallback_operation_source_archive_v3
        is not _EXPECTED_MANIFEST_REPLAY
        or OwnedFallbackRouteSegmentSessionV3 is not _EXPECTED_SESSION_CLASS
        or activate_owned_route_segment_v3 is not _EXPECTED_ACTIVATION
        or official_counter_registry_v1 is not _EXPECTED_V1_REGISTRY_FACTORY
    ):
        _fail("owned fallback runner or live kernel callable was substituted")


def _execute_authorized_owned_search_segment_v2(
    *,
    session: OwnedFallbackRouteSegmentSessionV3,
    kernel: Any,
    query: Any,
    proof: Mapping[str, Any],
    preexecution: acquisition_v1.CanonicalDirectFallbackPreexecutionCandidateV1,
    cap_profile: GroundFallbackCapProfileV1,
) -> tuple[GroundFallbackExecutionV1, OwnedRouteSegmentTranscriptV3]:
    """Execute the sole owner-bound search invocation for one session."""

    with activate_owned_route_segment_v3(session):
        session.enter()
        execution = run_owned_ground_fallback_search_v2(
            kernel,
            query,
            route_decision_context_id=(
                preexecution.route_context.route_decision_context_id
            ),
            decision_point_id=preexecution.decision_point.decision_point_id,
            route_decision_id=preexecution.decision.route_decision_id,
            selected_upper_id=(
                preexecution.upper.route_upper_bound_envelope_id
            ),
            route_attempt_id=preexecution.route_context.route_attempt_id,
            query_id=proof["identity"]["query_id"],
            cap_profile=cap_profile,
            registry=official_counter_registry_v1(),
            recorder_id="canonical-infeasible-fallback-owned-v2",
        )
        transcript = session.complete()
    return execution, transcript


_FROZEN_AUTHORIZED_SEARCH_CALLER_OBJECT_V2 = (
    _execute_authorized_owned_search_segment_v2
)
_FROZEN_AUTHORIZED_SEARCH_CALLER_GLOBALS_V2 = (
    _execute_authorized_owned_search_segment_v2.__globals__
)
_FROZEN_AUTHORIZED_SEARCH_CALLER_CODE_V2 = (
    _execute_authorized_owned_search_segment_v2.__code__
)


def run_canonical_infeasible_fallback_owned_v2(
    proof_bytes: bytes,
    *,
    current_identity: acquisition_v1.CanonicalFallbackCurrentIdentityV1,
    cap_profile: GroundFallbackCapProfileV1 | None = None,
) -> CanonicalOwnedFallbackRunnerResultV2:
    """Freeze authorization, execute one owned exact H1 segment, and verify it."""

    _require_live_callables()
    proof, _verified, current = acquisition_v1._proof_document(
        proof_bytes,
        current_identity=current_identity,
    )
    preexecution = acquisition_v1._preexecution_candidate(
        proof,
        current_identity=current,
        cap_profile=cap_profile,
    )
    if preexecution.decision.selected_route is not RouteSelection.FALLBACK:
        _fail("owned fallback runner did not freeze a FALLBACK decision")

    replay = manifest_v3.replay_direct_fallback_operation_source_archive_v3(
        manifest_v3.load_direct_fallback_operation_source_archive_v3()
    )
    if replay.manifest is None or replay.blockers:
        _fail("owned fallback production manifest failed exact source replay")
    manifest = replay.manifest
    route_segment_id = _content_id(
        _SUPPORT_DOMAIN,
        {
            "schema": "acfqp.canonical_owned_fallback_route_segment.v2",
            "preexecution_candidate_id": preexecution.candidate_id,
            "boundary_manifest_id": manifest.manifest_id,
        },
    )
    session = OwnedFallbackRouteSegmentSessionV3(
        route_segment_id=route_segment_id,
        occurrence_id=preexecution.route_context.logical_occurrence_id,
        route_attempt_id=preexecution.route_context.route_attempt_id,
        recorder_id="canonical-infeasible-fallback-owned-v2",
        boundary_manifest=manifest,
    )

    raw_kernel = G2048Kernel(2)
    query = acquisition_v1._canonical_query(raw_kernel)
    acquisition_v1._verify_initial_law(query, proof)
    traced_kernel = acquisition_v1._TracingKernel(raw_kernel)
    # The preexecution candidate, upper and decision are immutable above this
    # point.  No owned fallback transition occurred before session activation.
    _ = preexecution.candidate_id
    execution, transcript = _execute_authorized_owned_search_segment_v2(
        session=session,
        kernel=traced_kernel,
        query=query,
        proof=proof,
        preexecution=preexecution,
        cap_profile=preexecution.cap_profile,
    )

    trace_id = acquisition_v1._verify_live_execution(
        execution=execution,
        trace_rows=tuple(traced_kernel.rows),
        proof=proof,
        preexecution=preexecution,
    )
    if dict(transcript.values) != {
        path: execution.work_vector.values[path]
        for path in EXPECTED_VALUES
        if execution.work_vector.values[path] > 0
    }:
        _fail("owned positive-event transcript differs from exact solver counters")
    return CanonicalOwnedFallbackRunnerResultV2(
        _ISSUER,
        hashlib.sha256(proof_bytes).hexdigest(),
        preexecution,
        manifest.manifest_id,
        replay.replay_id,
        trace_id,
        execution,
        transcript,
        "OWNED_EXACT_INFEASIBILITY_SEGMENT_VERIFIED",
    )


__all__ = (
    "COMPLETE_ACCOUNTING_CHAIN_ISSUED",
    "CONSTRUCTION_ONLY",
    "CanonicalOwnedFallbackRunnerResultV2",
    "ConstructionK7CanonicalInfeasibleFallbackOwnedRunnerV2Error",
    "EXPECTED_EVENT_COUNT",
    "EXPECTED_VALUES",
    "OFFICIAL_EXECUTION_ALLOWED",
    "PRODUCTION_OWNER_SOURCE_INTEGRATED",
    "PROFILE_KEY",
    "SCHEMA_VERSION",
    "TERMINAL_ARTIFACT_ISSUED",
    "run_canonical_infeasible_fallback_owned_v2",
)
