from __future__ import annotations

import dataclasses
from pathlib import Path
import sys

import pytest

from acfqp import construction_k7_canonical_infeasible_fallback_acquisition_v1 as acquisition_v1
from acfqp import construction_k7_direct_fallback_operation_boundary_manifest_v3 as manifest_v3
from acfqp.construction_accounting_route_segment_v3 import (
    ConstructionAccountingRouteSegmentV3Error,
    OwnedFallbackRouteSegmentSessionV3,
    OwnedRouteOperationEventV3,
    RouteSegmentTerminalKindV3,
    activate_owned_route_segment_v3,
    emit_owned_route_operation_v3,
)
from acfqp.construction_k7_canonical_infeasible_fallback_owned_runner_v2 import (
    EXPECTED_EVENT_COUNT,
    EXPECTED_VALUES,
    _execute_authorized_owned_search_segment_v2,
    run_canonical_infeasible_fallback_owned_v2,
)
from acfqp.domains.g2048 import G2048Kernel
from acfqp.phase3e_exact_infeasibility_durable_proof_v1 import (
    DurableExactInfeasibilityIdentityV1,
    issue_phase3e_exact_infeasibility_durable_proof_v1,
)
from acfqp.phase3e_fallback_v1 import (
    GroundFallbackOutcome,
    GroundFallbackProtocolError,
)
from acfqp.phase3e_ids import loads_canonical_json


ROOT = Path(__file__).resolve().parents[1]
CANONICAL_BUNDLE = ROOT / "artifacts" / "phase05" / "g2048"


@pytest.fixture(scope="module")
def proof_bytes() -> bytes:
    return issue_phase3e_exact_infeasibility_durable_proof_v1(CANONICAL_BUNDLE)


@pytest.fixture(scope="module")
def current_identity(proof_bytes: bytes):
    identity = DurableExactInfeasibilityIdentityV1.from_dict(
        loads_canonical_json(proof_bytes)["identity"]
    )
    return acquisition_v1.build_current_canonical_fallback_identity_v1(
        CANONICAL_BUNDLE,
        build_epoch_id=identity.build_epoch_id,
        threshold_profile_id=identity.threshold_profile_id,
        reward_profile_id=identity.reward_profile_id,
        policy_class_id=identity.policy_class_id,
        complete_search_profile_id=identity.complete_search_profile_id,
    )


@pytest.fixture(scope="module")
def owned_result(proof_bytes: bytes, current_identity):
    return run_canonical_infeasible_fallback_owned_v2(
        proof_bytes, current_identity=current_identity
    )


@pytest.fixture(scope="module")
def frozen_manifest():
    return manifest_v3.freeze_direct_fallback_operation_boundary_manifest_v3()


def _preexecution(proof_bytes: bytes, current_identity):
    proof, _verified, current = acquisition_v1._proof_document(
        proof_bytes, current_identity=current_identity
    )
    pre = acquisition_v1._preexecution_candidate(
        proof, current_identity=current, cap_profile=None
    )
    return proof, pre


def _session(pre, suffix: str) -> OwnedFallbackRouteSegmentSessionV3:
    return OwnedFallbackRouteSegmentSessionV3(
        route_segment_id=pre.candidate_id,
        occurrence_id=pre.route_context.logical_occurrence_id,
        route_attempt_id=pre.route_context.route_attempt_id,
        recorder_id=f"owned-fallback-test-{suffix}",
        boundary_manifest=manifest_v3.freeze_direct_fallback_operation_boundary_manifest_v3(),
    )


def _session_with_manifest(pre, suffix: str, manifest) -> OwnedFallbackRouteSegmentSessionV3:
    return OwnedFallbackRouteSegmentSessionV3(
        route_segment_id=pre.candidate_id,
        occurrence_id=pre.route_context.logical_occurrence_id,
        route_attempt_id=pre.route_context.route_attempt_id,
        recorder_id=f"owned-fallback-test-{suffix}",
        boundary_manifest=manifest,
    )


def _run_direct(session, kernel, query, proof, pre, cap):
    return _execute_authorized_owned_search_segment_v2(
        session=session,
        kernel=kernel,
        query=query,
        proof=proof,
        preexecution=pre,
        cap_profile=cap,
    )


def test_owned_runner_exact_h1_infeasibility_and_208_events(owned_result) -> None:
    assert owned_result.execution.result.outcome is GroundFallbackOutcome.INFEASIBLE_CERTIFIED
    assert owned_result.execution.result.search_complete is True
    assert owned_result.execution.selected_policy is None
    assert len(owned_result.transcript.events) == EXPECTED_EVENT_COUNT == 208
    assert dict(owned_result.transcript.values) == {
        path: value for path, value in EXPECTED_VALUES.items() if value > 0
    }
    assert {
        path: owned_result.execution.work_vector.values[path]
        for path in EXPECTED_VALUES
    } == EXPECTED_VALUES
    document = owned_result.to_document()
    assert document["selected_route_frozen_before_ground_access"] is True
    assert document["production_owner_source_integrated"] is True
    assert document["complete_accounting_chain_issued"] is False
    assert document["counter_records_issued"] == 0
    assert document["terminal_artifact_issued"] is False
    assert document["official_execution_allowed"] is False


def test_each_event_is_literal_unit_and_bound_to_the_real_owner(owned_result) -> None:
    manifest = manifest_v3.freeze_direct_fallback_operation_boundary_manifest_v3()
    by_dispatch = manifest.by_dispatch
    assert all(type(row) is OwnedRouteOperationEventV3 for row in owned_result.transcript.events)
    for sequence, event in enumerate(owned_result.transcript.events, start=1):
        boundary = by_dispatch[event.dispatch_key]
        assert event.event_sequence == sequence
        assert event.amount == 1
        assert event.path == boundary.target_path
        assert event.boundary_id == boundary.boundary_id


def test_cap_exhaustion_records_rejection_and_completes_noncertificate_segment(
    proof_bytes: bytes, current_identity
) -> None:
    proof, pre = _preexecution(proof_bytes, current_identity)
    cap = dataclasses.replace(pre.cap_profile, max_states_expanded=7)
    kernel = G2048Kernel(2)
    query = acquisition_v1._canonical_query(kernel)
    session = _session(pre, "cap")
    execution, transcript = _run_direct(
        session, kernel, query, proof, pre, cap
    )
    assert execution.result.outcome is GroundFallbackOutcome.CAP_EXHAUSTED
    assert execution.result.search_complete is False
    assert execution.result.frontier == ()
    assert execution.selected_policy is None
    assert transcript.terminal.terminal_kind is RouteSegmentTerminalKindV3.COMPLETED
    assert transcript.values["control.cap_rejections"] == 1
    assert transcript.values["fallback.states_expanded"] == 7


def test_kernel_exception_retains_reserved_ground_step_in_aborted_prefix(
    proof_bytes: bytes, current_identity
) -> None:
    proof, pre = _preexecution(proof_bytes, current_identity)
    raw = G2048Kernel(2)

    class ExplodingKernel:
        def __getattr__(self, name):
            return getattr(raw, name)

        def step(self, state, action):
            raise RuntimeError("injected kernel failure")

    kernel = ExplodingKernel()
    query = acquisition_v1._canonical_query(raw)
    session = _session(pre, "kernel-error")
    with pytest.raises(RuntimeError, match="injected kernel failure"):
        _run_direct(session, kernel, query, proof, pre, pre.cap_profile)
    transcript = session.transcript
    assert transcript.terminal.terminal_kind is RouteSegmentTerminalKindV3.ABORTED
    assert transcript.values["fallback.ground_steps"] == 1
    assert transcript.values.get("fallback.outcome_rows", 0) == 0
    assert transcript.terminal.abort_reason == "ACTIVE_SCOPE_EXCEPTION"


def test_oversized_outcome_failure_retains_every_observed_positive_row(
    proof_bytes: bytes, current_identity
) -> None:
    proof, pre = _preexecution(proof_bytes, current_identity)
    cap = dataclasses.replace(pre.cap_profile, max_positive_outcomes_per_step=5)
    kernel = G2048Kernel(2)
    query = acquisition_v1._canonical_query(kernel)
    session = _session(pre, "oversized-outcomes")
    with pytest.raises(GroundFallbackProtocolError) as raised:
        _run_direct(session, kernel, query, proof, pre, cap)
    transcript = session.transcript
    assert transcript.terminal.terminal_kind is RouteSegmentTerminalKindV3.ABORTED
    assert transcript.values["fallback.ground_steps"] == 1
    assert transcript.values["fallback.outcome_rows"] == 6
    assert raised.value.partial_work_vector is not None
    assert raised.value.partial_work_vector.values["fallback.ground_steps"] == 1
    assert raised.value.partial_work_vector.values["fallback.outcome_rows"] == 6


def test_direct_gateway_spoof_aborts_and_retains_no_fake_event(
    proof_bytes: bytes, current_identity
) -> None:
    _proof, pre = _preexecution(proof_bytes, current_identity)
    session = _session(pre, "spoof")
    with pytest.raises(
        ConstructionAccountingRouteSegmentV3Error,
        match="bound search invocation",
    ):
        with activate_owned_route_segment_v3(session):
            session.enter()
            emit_owned_route_operation_v3("direct-fallback.state.expanded", 1)
    assert session.transcript.terminal.terminal_kind is RouteSegmentTerminalKindV3.ABORTED
    assert session.transcript.events == ()


def test_route_nodes_cannot_be_minted_with_readable_token(owned_result) -> None:
    import acfqp.construction_accounting_route_segment_v3 as route_v3

    event = owned_result.transcript.events[0]
    with pytest.raises(ConstructionAccountingRouteSegmentV3Error, match="session issuer"):
        route_v3.OwnedRouteOperationEventV3(
            route_v3._NODE_ISSUER,
            event.route_segment_start_id,
            event.boundary_id,
            event.dispatch_key,
            event.path,
            event.amount,
            event.event_sequence,
            event.predecessor_chain_id,
        )


def test_session_rejects_runtime_class_replacement_before_ground(
    monkeypatch: pytest.MonkeyPatch,
    proof_bytes: bytes,
    current_identity,
) -> None:
    from acfqp import phase3e_fallback_owned_v2 as owned_v2

    _proof, pre = _preexecution(proof_bytes, current_identity)
    manifest = manifest_v3.freeze_direct_fallback_operation_boundary_manifest_v3()
    fake = type(
        "_OwnedFallbackLedgerV2",
        (),
        {"__module__": owned_v2.__name__},
    )
    monkeypatch.setattr(owned_v2, "_OwnedFallbackLedgerV2", fake)
    with pytest.raises(
        ConstructionAccountingRouteSegmentV3Error,
        match="import-time live source binding",
    ):
        _session_with_manifest(pre, "replaced-class", manifest)


def test_session_rejects_runtime_method_replacement_before_ground(
    monkeypatch: pytest.MonkeyPatch,
    proof_bytes: bytes,
    current_identity,
) -> None:
    from acfqp import phase3e_fallback_owned_v2 as owned_v2

    _proof, pre = _preexecution(proof_bytes, current_identity)
    manifest = manifest_v3.freeze_direct_fallback_operation_boundary_manifest_v3()

    def fake_expand(self) -> None:
        emit_owned_route_operation_v3("direct-fallback.state.expanded", 1)

    monkeypatch.setattr(owned_v2._OwnedFallbackLedgerV2, "expand_state", fake_expand)
    with pytest.raises(
        ConstructionAccountingRouteSegmentV3Error,
        match="import-time live source binding",
    ):
        _session_with_manifest(pre, "replaced-method", manifest)


def test_same_name_same_literal_exec_class_cannot_mint_completed_event(
    monkeypatch: pytest.MonkeyPatch,
    proof_bytes: bytes,
    current_identity,
) -> None:
    from acfqp import phase3e_fallback_owned_v2 as owned_v2

    _proof, pre = _preexecution(proof_bytes, current_identity)
    manifest = manifest_v3.freeze_direct_fallback_operation_boundary_manifest_v3()
    namespace = {
        "__name__": owned_v2.__name__,
        "emit_owned_route_operation_v3": emit_owned_route_operation_v3,
    }
    exec(
        "class _OwnedFallbackLedgerV2:\n"
        "    def expand_state(self):\n"
        "        emit_owned_route_operation_v3('direct-fallback.state.expanded', 1)\n",
        namespace,
    )
    monkeypatch.setattr(
        owned_v2,
        "_OwnedFallbackLedgerV2",
        namespace["_OwnedFallbackLedgerV2"],
    )
    with pytest.raises(
        ConstructionAccountingRouteSegmentV3Error,
        match="import-time live source binding",
    ):
        _session_with_manifest(pre, "exec-forgery", manifest)


def test_runner_checks_import_time_class_methods_and_gateway_before_execution(
    monkeypatch: pytest.MonkeyPatch,
    proof_bytes: bytes,
    current_identity,
) -> None:
    from acfqp import phase3e_fallback_owned_v2 as owned_v2
    from acfqp.construction_k7_canonical_infeasible_fallback_owned_runner_v2 import (
        ConstructionK7CanonicalInfeasibleFallbackOwnedRunnerV2Error,
        run_canonical_infeasible_fallback_owned_v2,
    )

    original = owned_v2._OwnedFallbackLedgerV2

    class FakeLedger(original):
        pass

    FakeLedger.__name__ = "_OwnedFallbackLedgerV2"
    FakeLedger.__qualname__ = "_OwnedFallbackLedgerV2"
    monkeypatch.setattr(owned_v2, "_OwnedFallbackLedgerV2", FakeLedger)
    with pytest.raises(
        ConstructionK7CanonicalInfeasibleFallbackOwnedRunnerV2Error,
        match="import-time class/method binding",
    ):
        run_canonical_infeasible_fallback_owned_v2(
            proof_bytes, current_identity=current_identity
        )


def test_session_rejects_owned_module_gateway_replacement_before_ground(
    monkeypatch: pytest.MonkeyPatch,
    proof_bytes: bytes,
    current_identity,
) -> None:
    from acfqp import phase3e_fallback_owned_v2 as owned_v2

    _proof, pre = _preexecution(proof_bytes, current_identity)
    manifest = manifest_v3.freeze_direct_fallback_operation_boundary_manifest_v3()
    monkeypatch.setattr(
        owned_v2,
        "emit_owned_route_operation_v3",
        lambda dispatch_key, amount=1: None,
    )
    with pytest.raises(
        ConstructionAccountingRouteSegmentV3Error,
        match="import-time live source binding",
    ):
        _session_with_manifest(pre, "replaced-gateway", manifest)


def test_session_revalidates_import_time_class_after_construction_before_enter(
    monkeypatch: pytest.MonkeyPatch,
    proof_bytes: bytes,
    current_identity,
) -> None:
    from acfqp import phase3e_fallback_owned_v2 as owned_v2

    _proof, pre = _preexecution(proof_bytes, current_identity)
    manifest = manifest_v3.freeze_direct_fallback_operation_boundary_manifest_v3()
    session = _session_with_manifest(pre, "late-replaced-class", manifest)
    fake = type(
        "_OwnedFallbackLedgerV2",
        (),
        {"__module__": owned_v2.__name__},
    )
    monkeypatch.setattr(owned_v2, "_OwnedFallbackLedgerV2", fake)
    with pytest.raises(
        ConstructionAccountingRouteSegmentV3Error,
        match="import-time owner binding",
    ):
        session.enter()
    assert session.transcript.terminal.terminal_kind is RouteSegmentTerminalKindV3.ABORTED
    assert session.transcript.events == ()


def test_runner_rejects_owned_gateway_replacement_before_execution(
    monkeypatch: pytest.MonkeyPatch,
    proof_bytes: bytes,
    current_identity,
) -> None:
    from acfqp import phase3e_fallback_owned_v2 as owned_v2
    from acfqp.construction_k7_canonical_infeasible_fallback_owned_runner_v2 import (
        ConstructionK7CanonicalInfeasibleFallbackOwnedRunnerV2Error,
        run_canonical_infeasible_fallback_owned_v2,
    )

    monkeypatch.setattr(
        owned_v2,
        "emit_owned_route_operation_v3",
        lambda dispatch_key, amount=1: None,
    )
    with pytest.raises(
        ConstructionK7CanonicalInfeasibleFallbackOwnedRunnerV2Error,
        match="import-time class/method binding",
    ):
        run_canonical_infeasible_fallback_owned_v2(
            proof_bytes, current_identity=current_identity
        )


def test_transient_gateway_noop_restore_is_rejected_before_counter_mutation(
    monkeypatch: pytest.MonkeyPatch,
    proof_bytes: bytes,
    current_identity,
    frozen_manifest,
) -> None:
    from acfqp import construction_accounting_route_segment_v3 as route_v3

    proof, pre = _preexecution(proof_bytes, current_identity)
    session = _session_with_manifest(pre, "gateway-code", frozen_manifest)
    original_code = route_v3.emit_owned_route_operation_v3.__code__
    monkeypatch.setitem(
        route_v3.__dict__,
        "_TEST_TRANSIENT_GATEWAY_ORIGINAL_CODE_V3",
        original_code,
    )
    namespace = {}
    exec(
        "def transient_noop(dispatch_key, amount=1):\n"
        "    emit_owned_route_operation_v3.__code__ = "
        "_TEST_TRANSIENT_GATEWAY_ORIGINAL_CODE_V3\n"
        "    return None\n",
        route_v3.__dict__,
        namespace,
    )
    replacement_code = namespace["transient_noop"].__code__
    raw = G2048Kernel(2)

    class TransientGatewayKernel:
        def __getattr__(self, name):
            return getattr(raw, name)

        def actions(self, state):
            actions = raw.actions(state)
            if session._bound_ledger is not None:
                route_v3.emit_owned_route_operation_v3.__code__ = replacement_code
            return actions

    kernel = TransientGatewayKernel()
    query = acquisition_v1._canonical_query(raw)
    with pytest.raises(
        GroundFallbackProtocolError,
        match="event was not durably recorded",
    ) as raised:
        _run_direct(session, kernel, query, proof, pre, pre.cap_profile)
    assert route_v3.emit_owned_route_operation_v3.__code__ is original_code
    assert session.transcript.terminal.terminal_kind is RouteSegmentTerminalKindV3.ABORTED
    assert dict(session.transcript.values) == {
        "control.cap_checks": 1,
        "fallback.states_expanded": 1,
    }
    assert raised.value.partial_work_vector is not None
    assert raised.value.partial_work_vector.values["control.cap_checks"] == 1
    assert raised.value.partial_work_vector.values["fallback.states_expanded"] == 1
    assert raised.value.partial_work_vector.values["fallback.bellman_backups"] == 0


def test_direct_real_ledger_driving_cannot_mint_completed_transcript(
    proof_bytes: bytes,
    current_identity,
    frozen_manifest,
) -> None:
    from acfqp import phase3e_fallback_owned_v2 as owned_v2

    _proof, pre = _preexecution(proof_bytes, current_identity)
    session = _session_with_manifest(pre, "direct-ledger", frozen_manifest)
    ledger = owned_v2._OwnedFallbackLedgerV2(pre.cap_profile)
    with activate_owned_route_segment_v3(session):
        session.enter()
        with pytest.raises(
            ConstructionAccountingRouteSegmentV3Error,
            match="bound search invocation",
        ):
            ledger.expand_state()
    assert ledger.cap_checks == 0
    assert ledger.states_expanded == 0
    assert session.transcript.terminal.terminal_kind is RouteSegmentTerminalKindV3.ABORTED
    assert session.transcript.events == ()


def test_readable_private_bind_issuer_cannot_bypass_frozen_wrapper(
    proof_bytes: bytes,
    current_identity,
    frozen_manifest,
) -> None:
    from acfqp import construction_accounting_route_segment_v3 as route_v3
    from acfqp import phase3e_fallback_owned_v2 as owned_v2

    _proof, pre = _preexecution(proof_bytes, current_identity)
    session = _session_with_manifest(pre, "private-bind", frozen_manifest)
    ledger = owned_v2._OwnedFallbackLedgerV2(pre.cap_profile)
    with pytest.raises(
        ConstructionAccountingRouteSegmentV3Error,
        match="bypassed its frozen wrapper",
    ):
        with activate_owned_route_segment_v3(session):
            session.enter()
            session._bind_search_from_owner(
                route_v3._SEARCH_BIND_ISSUER_V3,
                ledger,
                sys._getframe(),
            )
    assert ledger.cap_checks == 0
    assert session.transcript.terminal.terminal_kind is RouteSegmentTerminalKindV3.ABORTED
    assert session.transcript.events == ()


def test_readable_private_finish_issuer_cannot_bypass_frozen_wrapper(
    proof_bytes: bytes,
    current_identity,
    frozen_manifest,
) -> None:
    from acfqp import construction_accounting_route_segment_v3 as route_v3
    from acfqp import phase3e_fallback_owned_v2 as owned_v2

    _proof, pre = _preexecution(proof_bytes, current_identity)
    session = _session_with_manifest(pre, "private-finish", frozen_manifest)
    ledger = owned_v2._OwnedFallbackLedgerV2(pre.cap_profile)
    with pytest.raises(
        ConstructionAccountingRouteSegmentV3Error,
        match="bypassed its frozen wrapper",
    ):
        with activate_owned_route_segment_v3(session):
            session.enter()
            session._finish_search_from_owner(
                route_v3._SEARCH_FINISH_ISSUER_V3,
                ledger,
                sys._getframe(),
            )
    assert ledger.cap_checks == 0
    assert session.transcript.terminal.terminal_kind is RouteSegmentTerminalKindV3.ABORTED
    assert session.transcript.events == ()


def test_transient_search_authorizer_restore_cannot_bind_external_frame(
    monkeypatch: pytest.MonkeyPatch,
    proof_bytes: bytes,
    current_identity,
    frozen_manifest,
) -> None:
    from acfqp import construction_accounting_route_segment_v3 as route_v3
    from acfqp import phase3e_fallback_owned_v2 as owned_v2

    _proof, pre = _preexecution(proof_bytes, current_identity)
    session = _session_with_manifest(pre, "transient-authorizer", frozen_manifest)
    ledger = owned_v2._OwnedFallbackLedgerV2(pre.cap_profile)
    original = route_v3._require_authorized_owned_search_frame_v3

    def transient_authorizer(_search_frame) -> None:
        setattr(
            route_v3,
            "_require_authorized_owned_search_frame_v3",
            original,
        )

    monkeypatch.setattr(
        route_v3,
        "_require_authorized_owned_search_frame_v3",
        transient_authorizer,
    )
    with pytest.raises(
        ConstructionAccountingRouteSegmentV3Error,
        match="lacks its frozen authorized caller",
    ):
        with activate_owned_route_segment_v3(session):
            session.enter()
            route_v3.bind_owned_fallback_search_v3(ledger)
    assert route_v3._require_authorized_owned_search_frame_v3 is original
    assert ledger.cap_checks == 0
    assert session.transcript.terminal.terminal_kind is RouteSegmentTerminalKindV3.ABORTED
    assert session.transcript.events == ()


@pytest.mark.parametrize(
    "method_name",
    (
        "_guard",
        "_reject",
        "expand_state",
        "evaluate_action",
        "reserve_transition",
        "record_outcomes",
        "compose_candidate",
    ),
)
def test_in_place_owner_method_code_replacement_is_rejected_before_session(
    monkeypatch: pytest.MonkeyPatch,
    proof_bytes: bytes,
    current_identity,
    frozen_manifest,
    method_name: str,
) -> None:
    from acfqp import phase3e_fallback_owned_v2 as owned_v2

    _proof, pre = _preexecution(proof_bytes, current_identity)
    function = getattr(owned_v2._OwnedFallbackLedgerV2, method_name)
    replacement = lambda self, *args, **kwargs: None
    monkeypatch.setattr(function, "__code__", replacement.__code__)
    with pytest.raises(
        ConstructionAccountingRouteSegmentV3Error,
        match="import-time live source binding",
    ):
        _session_with_manifest(pre, f"method-code-{method_name}", frozen_manifest)


def test_in_place_owner_validator_code_replacement_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
    proof_bytes: bytes,
    current_identity,
    frozen_manifest,
) -> None:
    from acfqp import phase3e_fallback_owned_v2 as owned_v2

    _proof, pre = _preexecution(proof_bytes, current_identity)
    replacement = lambda *args, **kwargs: None
    monkeypatch.setattr(
        owned_v2.require_frozen_owned_fallback_source_binding_v2,
        "__code__",
        replacement.__code__,
    )
    with pytest.raises(
        ConstructionAccountingRouteSegmentV3Error,
        match="import-time live source binding",
    ):
        _session_with_manifest(pre, "owner-validator-code", frozen_manifest)


def test_in_place_manifest_validator_code_replacement_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
    proof_bytes: bytes,
    current_identity,
    frozen_manifest,
) -> None:
    _proof, pre = _preexecution(proof_bytes, current_identity)
    replacement = lambda *args, **kwargs: None
    monkeypatch.setattr(
        manifest_v3.require_frozen_live_owner_binding_v3,
        "__code__",
        replacement.__code__,
    )
    with pytest.raises(
        ConstructionAccountingRouteSegmentV3Error,
        match="live-binding validator changed",
    ):
        _session_with_manifest(pre, "manifest-validator-code", frozen_manifest)


def test_runner_rejects_in_place_gateway_code_replacement_before_ground(
    monkeypatch: pytest.MonkeyPatch,
    proof_bytes: bytes,
    current_identity,
) -> None:
    from acfqp import construction_accounting_route_segment_v3 as route_v3
    from acfqp.construction_k7_canonical_infeasible_fallback_owned_runner_v2 import (
        ConstructionK7CanonicalInfeasibleFallbackOwnedRunnerV2Error,
        run_canonical_infeasible_fallback_owned_v2,
    )

    replacement = lambda dispatch_key, amount=1: None
    monkeypatch.setattr(
        route_v3.emit_owned_route_operation_v3,
        "__code__",
        replacement.__code__,
    )
    with pytest.raises(
        ConstructionK7CanonicalInfeasibleFallbackOwnedRunnerV2Error,
        match="import-time class/method binding",
    ):
        run_canonical_infeasible_fallback_owned_v2(
            proof_bytes, current_identity=current_identity
        )


def test_event_boundary_rejects_class_replacement_without_appending_event(
    monkeypatch: pytest.MonkeyPatch,
    proof_bytes: bytes,
    current_identity,
    frozen_manifest,
) -> None:
    from acfqp import phase3e_fallback_owned_v2 as owned_v2

    _proof, pre = _preexecution(proof_bytes, current_identity)
    session = _session_with_manifest(pre, "event-class-change", frozen_manifest)
    ledger = owned_v2._OwnedFallbackLedgerV2(pre.cap_profile)
    with activate_owned_route_segment_v3(session):
        session.enter()
        replacement = type(
            "_OwnedFallbackLedgerV2",
            (),
            {"__module__": owned_v2.__name__},
        )
        monkeypatch.setattr(owned_v2, "_OwnedFallbackLedgerV2", replacement)
        with pytest.raises(
            ConstructionAccountingRouteSegmentV3Error,
            match="import-time owner binding",
        ):
            ledger.expand_state()
    assert ledger.cap_checks == 0
    assert ledger.states_expanded == 0
    assert session.transcript.terminal.terminal_kind is RouteSegmentTerminalKindV3.ABORTED
    assert session.transcript.events == ()


def test_event_boundary_rejects_validator_change_without_appending_event(
    monkeypatch: pytest.MonkeyPatch,
    proof_bytes: bytes,
    current_identity,
    frozen_manifest,
) -> None:
    _proof, pre = _preexecution(proof_bytes, current_identity)
    session = _session_with_manifest(pre, "event-validator-change", frozen_manifest)
    from acfqp import phase3e_fallback_owned_v2 as owned_v2

    ledger = owned_v2._OwnedFallbackLedgerV2(pre.cap_profile)
    with activate_owned_route_segment_v3(session):
        session.enter()
        replacement = lambda manifest: None
        monkeypatch.setattr(
            manifest_v3,
            "require_frozen_live_owner_binding_v3",
            replacement,
        )
        with pytest.raises(
            ConstructionAccountingRouteSegmentV3Error,
            match="live-binding validator changed",
        ):
            ledger.expand_state()
    assert ledger.cap_checks == 0
    assert ledger.states_expanded == 0
    assert session.transcript.terminal.terminal_kind is RouteSegmentTerminalKindV3.ABORTED
    assert session.transcript.events == ()
