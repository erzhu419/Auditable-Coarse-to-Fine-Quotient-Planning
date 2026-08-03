from __future__ import annotations

from contextvars import copy_context
from dataclasses import replace
import hashlib
import threading
from types import SimpleNamespace

import pytest

from acfqp import construction_accounting_registry_v6 as registry_v6
from acfqp import construction_accounting_route_segment_v2 as runtime_v2
from acfqp import (
    construction_k7_direct_fallback_operation_boundary_manifest_v2 as manifest_v2,
)


def _id(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _session(label: str = "base") -> runtime_v2.RouteSegmentAccountingSessionV2:
    return runtime_v2.RouteSegmentAccountingSessionV2(
        route_segment_id=_id(f"segment:{label}"),
        occurrence_id=_id(f"occurrence:{label}"),
        route_attempt_id=_id(f"attempt:{label}"),
        recorder_id=f"route-segment-{label}-v2",
        stage_kind=registry_v6.ConstructionStageKindV6.DIRECT_FALLBACK,
        boundary_manifest=(
            manifest_v2.freeze_direct_fallback_operation_boundary_manifest_v2()
        ),
    )


_SOURCE_METHODS = (
    runtime_v2.DirectFallbackOwnedOperationSourceV2.cap_check_v2,
    runtime_v2.DirectFallbackOwnedOperationSourceV2.cap_rejection_v2,
    runtime_v2.DirectFallbackOwnedOperationSourceV2.state_expanded_v2,
    runtime_v2.DirectFallbackOwnedOperationSourceV2.action_evaluated_v2,
    runtime_v2.DirectFallbackOwnedOperationSourceV2.ground_step_v2,
    runtime_v2.DirectFallbackOwnedOperationSourceV2.outcome_row_v2,
    runtime_v2.DirectFallbackOwnedOperationSourceV2.bellman_backup_v2,
)


def test_inactive_source_hooks_are_exact_noops() -> None:
    for method in _SOURCE_METHODS:
        assert method() is None
    assert runtime_v2.complete_route_segment_v2() is None


def test_exact_direct_fallback_segment_chain_completes() -> None:
    session = _session("complete")
    stage = registry_v6.ConstructionStageKindV6.DIRECT_FALLBACK
    with runtime_v2.activate_route_segment_accounting_v2(session):
        runtime_v2.enter_route_segment_stage_v2(stage)
        for method in _SOURCE_METHODS:
            method()
        runtime_v2.exit_route_segment_stage_v2(stage)
        transcript = runtime_v2.complete_route_segment_v2()

    assert transcript is not None
    assert transcript == session.transcript
    assert transcript.terminal_kind is runtime_v2.RouteSegmentTerminalKindV2.COMPLETED
    assert len(transcript.event_ids) == 7
    event_paths = tuple(
        node.path
        for node in transcript.nodes
        if type(node) is runtime_v2.RouteSegmentOperationEventV2
    )
    assert set(event_paths) == {
        "control.cap_checks",
        "control.cap_rejections",
        "fallback.states_expanded",
        "fallback.actions_evaluated",
        "fallback.ground_steps",
        "fallback.outcome_rows",
        "fallback.bellman_backups",
    }
    document = transcript.to_document()
    assert document["absent_event_is_zero"] is False
    assert document["counter_records_issued"] == 0
    assert document["work_vectors_issued"] == 0
    assert document["comparison_vectors_issued"] == 0
    assert document["central_domain_registration_pending"] is True
    assert document["production_closure_claimed"] is False
    assert document["construction_only"] is True
    assert document["python_api_spoof_resistance_only"] is True
    assert document["native_code_adversary_resistance_claimed"] is False


def test_direct_public_dispatch_cannot_spoof_frozen_owner() -> None:
    session = _session("spoof")
    stage = registry_v6.ConstructionStageKindV6.DIRECT_FALLBACK
    with pytest.raises(
        runtime_v2.ConstructionAccountingRouteSegmentV2Error,
        match="frozen source owner",
    ):
        with runtime_v2.activate_route_segment_accounting_v2(session):
            session.enter_stage(stage)
            runtime_v2.emit_route_segment_operation_v2(
                "direct-fallback.control.cap-check", 1
            )
    assert session.transcript.terminal_kind is runtime_v2.RouteSegmentTerminalKindV2.ABORTED
    assert session.transcript.to_document()["nodes"][-1]["reason"] == (
        "OPERATION_OWNER_MISMATCH"
    )


def test_direct_session_emission_is_forbidden_and_cannot_supply_caller_claims() -> None:
    session = _session("direct-session-spoof")
    stage = registry_v6.ConstructionStageKindV6.DIRECT_FALLBACK
    with pytest.raises(
        runtime_v2.ConstructionAccountingRouteSegmentV2Error,
        match="frozen gateway",
    ):
        with runtime_v2.activate_route_segment_accounting_v2(session):
            session.enter_stage(stage)
            session.emit_operation()
    assert session.transcript.to_document()["nodes"][-1]["reason"] == (
        "DIRECT_SESSION_EMISSION_FORBIDDEN"
    )
    with pytest.raises(TypeError):
        session.emit_operation(  # type: ignore[call-arg]
            "direct-fallback.control.cap-check",
            caller_module=runtime_v2.__name__,
            caller_globals=runtime_v2.__dict__,
            caller_code=lambda: None,
        )


def test_private_gateway_entry_rejects_even_real_token_and_forged_owner_claims() -> None:
    session = _session("private-gateway-spoof")
    stage = registry_v6.ConstructionStageKindV6.DIRECT_FALLBACK
    owner = runtime_v2.DirectFallbackOwnedOperationSourceV2.cap_check_v2
    with pytest.raises(
        runtime_v2.ConstructionAccountingRouteSegmentV2Error,
        match="immediate frozen gateway",
    ):
        with runtime_v2.activate_route_segment_accounting_v2(session):
            session.enter_stage(stage)
            session._emit_from_gateway(  # noqa: SLF001
                runtime_v2._GATEWAY_ISSUER,  # noqa: SLF001
                "direct-fallback.control.cap-check",
                1,
                owner_module=runtime_v2.__name__,
                owner_globals=runtime_v2.__dict__,
                owner_code=owner.__code__,
            )
    assert session.transcript.to_document()["nodes"][-1]["reason"] == (
        "UNTRUSTED_GATEWAY_CALLER"
    )


def test_nonunit_amount_fails_before_owner_and_retains_abort() -> None:
    session = _session("amount")
    stage = registry_v6.ConstructionStageKindV6.DIRECT_FALLBACK
    with pytest.raises(
        runtime_v2.ConstructionAccountingRouteSegmentV2Error,
        match="one primitive",
    ):
        with runtime_v2.activate_route_segment_accounting_v2(session):
            session.enter_stage(stage)
            runtime_v2.emit_route_segment_operation_v2(
                "direct-fallback.control.cap-check", 2
            )
    assert session.transcript.to_document()["nodes"][-1]["reason"] == (
        "PRODUCTION_AMOUNT_NOT_UNIT"
    )


def test_explicit_abort_retains_positive_prefix() -> None:
    session = _session("abort")
    stage = registry_v6.ConstructionStageKindV6.DIRECT_FALLBACK
    with runtime_v2.activate_route_segment_accounting_v2(session):
        session.enter_stage(stage)
        runtime_v2.DirectFallbackOwnedOperationSourceV2.cap_check_v2()
        transcript = session.abort("CALLER_REQUESTED_ABORT")
    assert transcript.terminal_kind is runtime_v2.RouteSegmentTerminalKindV2.ABORTED
    assert len(transcript.event_ids) == 1
    assert transcript.to_document()["nodes"][-1]["positive_prefix_retained"] is True


def test_incomplete_completion_and_scope_exit_fail_closed() -> None:
    premature = _session("premature")
    with pytest.raises(
        runtime_v2.ConstructionAccountingRouteSegmentV2Error,
        match="before its exact stage",
    ):
        with runtime_v2.activate_route_segment_accounting_v2(premature):
            premature.complete()
    assert premature.transcript.to_document()["nodes"][-1]["reason"] == (
        "INCOMPLETE_ROUTE_SEGMENT"
    )

    incomplete = _session("scope-exit")
    with pytest.raises(
        runtime_v2.ConstructionAccountingRouteSegmentV2Error,
        match="without terminalization",
    ):
        with runtime_v2.activate_route_segment_accounting_v2(incomplete):
            incomplete.enter_stage(
                registry_v6.ConstructionStageKindV6.DIRECT_FALLBACK
            )
    assert incomplete.transcript.to_document()["nodes"][-1]["reason"] == (
        "INCOMPLETE_SCOPE_EXIT"
    )


def test_nested_and_cross_thread_use_fail_closed() -> None:
    outer = _session("outer")
    inner = _session("inner")
    with pytest.raises(
        runtime_v2.ConstructionAccountingRouteSegmentV2Error,
        match="nested",
    ):
        with runtime_v2.activate_route_segment_accounting_v2(outer):
            with runtime_v2.activate_route_segment_accounting_v2(inner):
                pass
    assert outer.transcript.to_document()["nodes"][-1]["reason"] == (
        "NESTED_ACTIVE_SCOPE"
    )

    cross_thread = _session("thread")
    errors: list[BaseException] = []
    context = copy_context()

    def invoke() -> None:
        try:
            context.run(
                cross_thread.enter_stage,
                registry_v6.ConstructionStageKindV6.DIRECT_FALLBACK,
            )
        except BaseException as error:  # retained for the owner-thread assertion
            errors.append(error)

    worker = threading.Thread(target=invoke)
    worker.start()
    worker.join()
    assert len(errors) == 1
    assert isinstance(
        errors[0], runtime_v2.ConstructionAccountingRouteSegmentV2Error
    )
    assert cross_thread.transcript.to_document()["nodes"][-1]["reason"] == (
        "CROSS_THREAD_ACTIVE_SCOPE"
    )


def test_wrong_v6_stage_aborts_without_partial_relabeling() -> None:
    session = _session("wrong-stage")
    with pytest.raises(
        runtime_v2.ConstructionAccountingRouteSegmentV2Error,
        match="another V6 route stage",
    ):
        with runtime_v2.activate_route_segment_accounting_v2(session):
            session.enter_stage(registry_v6.ConstructionStageKindV6.LOCAL_ATTEMPT)
    document = session.transcript.to_document()
    assert document["route_segment_start"]["stage_kind"] == "DIRECT_FALLBACK"
    assert document["nodes"][-1]["reason"] == "WRONG_ROUTE_STAGE"


def test_owner_symbol_mutation_after_binding_is_rejected_at_activation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _session("owner-mutation")
    monkeypatch.setattr(
        runtime_v2.DirectFallbackOwnedOperationSourceV2,
        "cap_check_v2",
        staticmethod(lambda: None),
    )
    with pytest.raises(
        runtime_v2.ConstructionAccountingRouteSegmentV2Error,
        match="source owner changed",
    ):
        with runtime_v2.activate_route_segment_accounting_v2(session):
            pass
    assert session.transcript.to_document()["nodes"][-1]["reason"] == (
        "LIVE_OWNER_BINDING_CHANGED"
    )


def test_gateway_mutation_after_binding_is_rejected_at_activation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _session("gateway-activation")
    monkeypatch.setattr(
        runtime_v2, "emit_route_segment_operation_v2", lambda *_args: None
    )
    with pytest.raises(
        runtime_v2.ConstructionAccountingRouteSegmentV2Error,
        match="gateway changed",
    ):
        with runtime_v2.activate_route_segment_accounting_v2(session):
            pass
    assert session.transcript.to_document()["nodes"][-1]["reason"] == (
        "LIVE_GATEWAY_BINDING_CHANGED"
    )


def test_gateway_mutation_inside_stage_is_rejected_before_exit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _session("gateway-exit")
    stage = registry_v6.ConstructionStageKindV6.DIRECT_FALLBACK
    with pytest.raises(
        runtime_v2.ConstructionAccountingRouteSegmentV2Error,
        match="gateway changed",
    ):
        with runtime_v2.activate_route_segment_accounting_v2(session):
            session.enter_stage(stage)
            runtime_v2.DirectFallbackOwnedOperationSourceV2.cap_check_v2()
            monkeypatch.setattr(
                runtime_v2, "emit_route_segment_operation_v2", lambda *_args: None
            )
            session.exit_stage(stage)
    transcript = session.transcript
    assert len(transcript.event_ids) == 1
    assert transcript.to_document()["nodes"][-1]["reason"] == (
        "LIVE_GATEWAY_BINDING_CHANGED"
    )


def test_owner_mutation_after_stage_exit_is_rejected_before_complete(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _session("owner-complete")
    stage = registry_v6.ConstructionStageKindV6.DIRECT_FALLBACK
    with pytest.raises(
        runtime_v2.ConstructionAccountingRouteSegmentV2Error,
        match="source owner changed",
    ):
        with runtime_v2.activate_route_segment_accounting_v2(session):
            session.enter_stage(stage)
            runtime_v2.DirectFallbackOwnedOperationSourceV2.cap_check_v2()
            session.exit_stage(stage)
            monkeypatch.setattr(
                runtime_v2.DirectFallbackOwnedOperationSourceV2,
                "cap_check_v2",
                staticmethod(lambda: None),
            )
            session.complete()
    transcript = session.transcript
    assert len(transcript.event_ids) == 1
    assert transcript.to_document()["nodes"][-1]["reason"] == (
        "LIVE_OWNER_BINDING_CHANGED"
    )


@pytest.mark.parametrize("mutation", ["delete", "noncallable"])
def test_removed_or_noncallable_live_owner_becomes_terminal_abort(
    monkeypatch: pytest.MonkeyPatch,
    mutation: str,
) -> None:
    session = _session(f"owner-{mutation}")
    if mutation == "delete":
        monkeypatch.delattr(
            runtime_v2.DirectFallbackOwnedOperationSourceV2, "cap_check_v2"
        )
    else:
        monkeypatch.setattr(
            runtime_v2.DirectFallbackOwnedOperationSourceV2,
            "cap_check_v2",
            None,
        )
    with pytest.raises(
        runtime_v2.ConstructionAccountingRouteSegmentV2Error,
        match="removed or made noncallable",
    ):
        with runtime_v2.activate_route_segment_accounting_v2(session):
            pass
    assert session.transcript.to_document()["nodes"][-1]["reason"] == (
        "LIVE_OWNER_BINDING_CHANGED"
    )


def test_duck_manifest_and_exact_type_path_relabel_are_rejected() -> None:
    official = manifest_v2.freeze_direct_fallback_operation_boundary_manifest_v2()

    class DuckManifest:
        boundary_manifest_id = official.boundary_manifest_id
        manifest_id = official.manifest_id
        counter_registry_id = official.counter_registry_id
        stage_profile_id = official.stage_profile_id
        stage_kind = official.stage_kind
        by_dispatch = official.by_dispatch

        @staticmethod
        def validate_official() -> None:
            return None

    with pytest.raises(
        runtime_v2.ConstructionAccountingRouteSegmentV2Error,
        match="exact direct-fallback manifest",
    ):
        runtime_v2.RouteSegmentAccountingSessionV2(
            route_segment_id=_id("segment:duck"),
            occurrence_id=_id("occurrence:duck"),
            route_attempt_id=_id("attempt:duck"),
            recorder_id="route-segment-duck-v2",
            stage_kind=registry_v6.ConstructionStageKindV6.DIRECT_FALLBACK,
            boundary_manifest=DuckManifest(),
        )

    relabelled_boundary = replace(
        official.boundaries[0], target_path="local.solver_subset_evaluations"
    )
    relabelled = replace(
        official,
        boundaries=tuple(
            sorted(
                (relabelled_boundary, *official.boundaries[1:]),
                key=lambda row: row.boundary_key,
            )
        ),
    )
    with pytest.raises(
        runtime_v2.ConstructionAccountingRouteSegmentV2Error,
        match="independent source replay",
    ):
        runtime_v2.RouteSegmentAccountingSessionV2(
            route_segment_id=_id("segment:relabel"),
            occurrence_id=_id("occurrence:relabel"),
            route_attempt_id=_id("attempt:relabel"),
            recorder_id="route-segment-relabel-v2",
            stage_kind=registry_v6.ConstructionStageKindV6.DIRECT_FALLBACK,
            boundary_manifest=relabelled,
        )


def test_chain_nodes_and_transcript_are_session_issued_only() -> None:
    manifest = manifest_v2.freeze_direct_fallback_operation_boundary_manifest_v2()
    stage = registry_v6.ConstructionStageKindV6.DIRECT_FALLBACK
    with pytest.raises(
        runtime_v2.ConstructionAccountingRouteSegmentV2Error,
        match="session-issued only",
    ):
        runtime_v2.RouteSegmentStartV2(
            object(),
            _id("minted-segment"),
            _id("minted-occurrence"),
            _id("minted-attempt"),
            registry_v6.official_counter_registry_v6().registry_id,
            registry_v6.official_stage_profile_v6().stage_profile_id,
            manifest.manifest_id,
            "caller-minted-v2",
            stage,
        )
    session = _session("minted-transcript")
    with pytest.raises(
        runtime_v2.ConstructionAccountingRouteSegmentV2Error,
        match="session-issued only",
    ):
        runtime_v2.RouteSegmentTranscriptV2(object(), session.start, ())


def test_readable_true_token_cannot_mint_start_abort_or_transcript() -> None:
    manifest = manifest_v2.freeze_direct_fallback_operation_boundary_manifest_v2()
    stage = registry_v6.ConstructionStageKindV6.DIRECT_FALLBACK
    registry = registry_v6.official_counter_registry_v6()
    profile = registry_v6.official_stage_profile_v6(registry)
    with pytest.raises(
        runtime_v2.ConstructionAccountingRouteSegmentV2Error,
        match="bypassed its exact session issuer",
    ):
        runtime_v2.RouteSegmentStartV2(
            runtime_v2._NODE_ISSUER,  # noqa: SLF001
            _id("true-token-segment"),
            _id("true-token-occurrence"),
            _id("true-token-attempt"),
            registry.registry_id,
            profile.stage_profile_id,
            manifest.manifest_id,
            "true-token-caller-v2",
            stage,
        )

    session = _session("true-token-terminal-nodes")
    with pytest.raises(
        runtime_v2.ConstructionAccountingRouteSegmentV2Error,
        match="bypassed its exact session issuer",
    ):
        runtime_v2.RouteSegmentAbortV2(
            runtime_v2._NODE_ISSUER,  # noqa: SLF001
            session.start.start_id,
            "CALLER_REQUESTED_ABORT",
            None,
            0,
            1,
            session.start.chain_id,
        )
    with pytest.raises(
        runtime_v2.ConstructionAccountingRouteSegmentV2Error,
        match="bypassed its exact session issuer",
    ):
        runtime_v2.RouteSegmentTranscriptV2(
            runtime_v2._NODE_ISSUER,  # noqa: SLF001
            session.start,
            (),
        )


def test_monkeypatched_sys_getframe_cannot_forge_gateway_or_node_ancestry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _session("getframe-gateway-attack")
    stage = registry_v6.ConstructionStageKindV6.DIRECT_FALLBACK
    owner = runtime_v2.DirectFallbackOwnedOperationSourceV2.cap_check_v2
    gateway = runtime_v2.emit_route_segment_operation_v2
    forged_frames = iter(
        (
            SimpleNamespace(f_globals=owner.__globals__, f_code=owner.__code__),
            SimpleNamespace(
                f_globals=gateway.__globals__, f_code=gateway.__code__
            ),
        )
    )
    caught: BaseException | None = None
    with runtime_v2.activate_route_segment_accounting_v2(session):
        session.enter_stage(stage)
        with monkeypatch.context() as scoped:
            scoped.setattr(
                runtime_v2.sys,
                "_getframe",
                lambda _depth=0: next(forged_frames),
            )
            try:
                runtime_v2.emit_route_segment_operation_v2(
                    "direct-fallback.control.cap-check", 1
                )
            except BaseException as error:
                caught = error
    assert isinstance(
        caught, runtime_v2.ConstructionAccountingRouteSegmentV2Error
    )
    assert "frozen source owner" in str(caught)
    assert session.transcript.to_document()["nodes"][-1]["reason"] == (
        "OPERATION_OWNER_MISMATCH"
    )

    manifest = manifest_v2.freeze_direct_fallback_operation_boundary_manifest_v2()
    registry = registry_v6.official_counter_registry_v6()
    profile = registry_v6.official_stage_profile_v6(registry)

    def forged_node_frame(depth: int = 0) -> SimpleNamespace:
        if depth == 2:
            return SimpleNamespace(
                f_code=runtime_v2.RouteSegmentStartV2.__init__.__code__
            )
        return SimpleNamespace(
            f_globals=runtime_v2.__dict__,
            f_code=runtime_v2.RouteSegmentAccountingSessionV2.__init__.__code__,
        )

    node_error: BaseException | None = None
    with monkeypatch.context() as scoped:
        scoped.setattr(runtime_v2.sys, "_getframe", forged_node_frame)
        try:
            runtime_v2.RouteSegmentStartV2(
                runtime_v2._NODE_ISSUER,  # noqa: SLF001
                _id("getframe-node-segment"),
                _id("getframe-node-occurrence"),
                _id("getframe-node-attempt"),
                registry.registry_id,
                profile.stage_profile_id,
                manifest.manifest_id,
                "getframe-node-caller-v2",
                stage,
            )
        except BaseException as error:
            node_error = error
    assert isinstance(
        node_error, runtime_v2.ConstructionAccountingRouteSegmentV2Error
    )
    assert "bypassed its exact session issuer" in str(node_error)
