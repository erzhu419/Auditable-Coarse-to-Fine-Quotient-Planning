from __future__ import annotations

from dataclasses import replace

import pytest

from acfqp import construction_k7_direct_fallback_operation_boundary_manifest_v3 as manifest_v3
from acfqp.construction_accounting_route_segment_v4 import (
    ConstructionAccountingRouteSegmentV4Error,
    EXPECTED_BOUNDARY_COUNT,
    OFFICIAL_EXECUTION_ALLOWED,
    OFFICIAL_N_BREAK_EVEN,
    OFFICIAL_SCALAR_COST,
    OwnedFallbackRouteSegmentSessionV4,
    OwnerRuntimeIntegrationBlockedV4,
    RouteOperationOriginV4,
    RouteSegmentTerminalKindV4,
    activate_construction_route_segment_v4,
    activate_owned_route_segment_v4,
    emit_verified_construction_operation_v4,
    verify_sealed_operation_boundary_authority_v4,
)
from acfqp.phase3e_ids import canonical_json_bytes, content_id


@pytest.fixture(scope="module")
def sealed_inputs():
    source = manifest_v3.load_direct_fallback_operation_source_archive_v3()[
        manifest_v3.SOURCE_MODULE
    ]
    document = canonical_json_bytes(
        manifest_v3.freeze_direct_fallback_operation_boundary_manifest_v3().to_document()
    )
    authority = verify_sealed_operation_boundary_authority_v4(source, document)
    return source, document, authority


def _identity(label: str) -> str:
    return content_id("acfqp:route-attempt:v1", {"test": label})


def _session(sealed_inputs, label: str) -> OwnedFallbackRouteSegmentSessionV4:
    source, document, authority = sealed_inputs
    return OwnedFallbackRouteSegmentSessionV4(
        route_segment_id=_identity(f"segment-{label}"),
        occurrence_id=_identity(f"occurrence-{label}"),
        route_attempt_id=_identity(f"attempt-{label}"),
        recorder_id="route-segment-v4-test",
        source_member_bytes=source,
        boundary_manifest_document_bytes=document,
        manifest_authority=authority,
    )


def _zero_values(authority) -> dict[str, int]:
    return {row.target_path: 0 for row in authority.boundaries}


def test_sealed_replay_never_uses_v3_live_loader_or_live_binding(
    monkeypatch: pytest.MonkeyPatch, sealed_inputs
) -> None:
    source, document, expected = sealed_inputs

    def explode(*_args, **_kwargs):
        raise AssertionError("live V3 repository authority must not be called")

    monkeypatch.setattr(
        manifest_v3, "load_direct_fallback_operation_source_archive_v3", explode
    )
    monkeypatch.setattr(manifest_v3, "require_frozen_live_owner_binding_v3", explode)
    actual = verify_sealed_operation_boundary_authority_v4(source, document)
    assert actual.to_document() == expected.to_document()
    assert len(actual.boundaries) == EXPECTED_BOUNDARY_COUNT == 7
    assert actual.runtime_gateway_compatible is False
    assert (
        actual.owner_integration_blocker.code
        == "SUCCESSOR_OWNED_ENGINE_IMPORTING_V4_GATEWAYS_REQUIRED"
    )
    assert actual.to_document()["ground_or_planner_work_performed_during_construction"] is False


def test_complete_construction_replay_preserves_seven_source_sites_and_prefix(
    sealed_inputs,
) -> None:
    session = _session(sealed_inputs, "complete")
    values = _zero_values(session.authority)
    with activate_construction_route_segment_v4(session):
        for boundary in session.authority.boundaries:
            assert emit_verified_construction_operation_v4(boundary.dispatch_key, 1)
            values[boundary.target_path] += 1
        session.finish_construction_harness(values)
        transcript = session.complete()

    assert transcript.terminal.terminal_kind is RouteSegmentTerminalKindV4.COMPLETED
    assert transcript.terminal.abort_reason is None
    assert len(transcript.events) == 7
    assert tuple(row.event_sequence for row in transcript.events) == tuple(range(1, 8))
    assert set(transcript.values) == set(values)
    assert dict(transcript.values) == values
    assert all(
        row.origin is RouteOperationOriginV4.CONSTRUCTION_VERIFIED_SOURCE_REPLAY
        and row.to_document()["source_owned_runtime_event"] is False
        for row in transcript.events
    )
    assert transcript.to_document()["absent_event_is_zero"] is False


def test_cap_rejection_abort_retains_exact_observed_positive_prefix(
    sealed_inputs,
) -> None:
    session = _session(sealed_inputs, "cap-abort")
    with activate_construction_route_segment_v4(session):
        emit_verified_construction_operation_v4(
            "direct-fallback.control.cap-check", 1
        )
        emit_verified_construction_operation_v4(
            "direct-fallback.control.cap-check", 1
        )
        emit_verified_construction_operation_v4(
            "direct-fallback.control.cap-rejection", 1
        )
        transcript = session.abort("CAP_EXHAUSTED_CONSTRUCTION_REPLAY")

    assert transcript.terminal.terminal_kind is RouteSegmentTerminalKindV4.ABORTED
    assert transcript.terminal.abort_reason == "CAP_EXHAUSTED_CONSTRUCTION_REPLAY"
    assert dict(transcript.values) == {
        "control.cap_checks": 2,
        "control.cap_rejections": 1,
    }
    assert transcript.to_document()["positive_prefix_retained"] is True
    assert "fallback.ground_steps" not in transcript.values


def test_finish_requires_full_exact_ledger_and_rejects_divergence(sealed_inputs) -> None:
    session = _session(sealed_inputs, "divergence")
    with pytest.raises(
        ConstructionAccountingRouteSegmentV4Error, match="seven ledger values"
    ):
        with activate_construction_route_segment_v4(session):
            emit_verified_construction_operation_v4(
                "direct-fallback.control.cap-check", 1
            )
            session.finish_construction_harness({"control.cap_checks": 1})
    assert session.transcript.terminal.terminal_kind is RouteSegmentTerminalKindV4.ABORTED
    assert dict(session.transcript.values) == {"control.cap_checks": 1}


def test_current_sealed_owner_cannot_enter_v4_runtime(sealed_inputs) -> None:
    session = _session(sealed_inputs, "runtime-blocked")
    with pytest.raises(OwnerRuntimeIntegrationBlockedV4) as raised:
        with activate_owned_route_segment_v4(session):
            raise AssertionError("unreachable")
    assert raised.value.blocker.blocker_id == session.owner_integration_blocker.blocker_id
    with pytest.raises(
        ConstructionAccountingRouteSegmentV4Error, match="before terminalization"
    ):
        _ = session.transcript


@pytest.mark.parametrize("which", ["source", "document"])
def test_mutated_sealed_inputs_fail_before_session(which: str, sealed_inputs) -> None:
    source, document, authority = sealed_inputs
    if which == "source":
        source = source[:-1] + bytes([source[-1] ^ 1])
    else:
        document = document[:-1] + b" "
    with pytest.raises(ConstructionAccountingRouteSegmentV4Error):
        OwnedFallbackRouteSegmentSessionV4(
            route_segment_id=_identity(f"mutated-{which}"),
            occurrence_id=_identity(f"mutated-occurrence-{which}"),
            route_attempt_id=_identity(f"mutated-attempt-{which}"),
            recorder_id="route-segment-v4-test",
            source_member_bytes=source,
            boundary_manifest_document_bytes=document,
            manifest_authority=authority,
        )


def test_caller_modified_authority_is_rejected(sealed_inputs) -> None:
    _source, _document, authority = sealed_inputs
    with pytest.raises(
        ConstructionAccountingRouteSegmentV4Error, match="verifier-issued"
    ):
        replace(
            authority,
            manifest_document_byte_count=authority.manifest_document_byte_count + 1,
            _issuer=object(),
        )


def test_official_locks_remain_closed() -> None:
    assert OFFICIAL_EXECUTION_ALLOWED is False
    assert OFFICIAL_SCALAR_COST is None
    assert OFFICIAL_N_BREAK_EVEN is None


def test_readable_module_issuer_cannot_mint_any_route_node_or_fake_owner_event(
    sealed_inputs,
) -> None:
    import acfqp.construction_accounting_route_segment_v4 as route_v4

    session = _session(sealed_inputs, "issuance-attack")
    values = _zero_values(session.authority)
    with activate_construction_route_segment_v4(session):
        boundary = session.authority.boundaries[0]
        emit_verified_construction_operation_v4(boundary.dispatch_key, 1)
        values[boundary.target_path] = 1
        session.finish_construction_harness(values)
        transcript = session.complete()

    start = transcript.start
    event = transcript.events[0]
    terminal = transcript.terminal
    with pytest.raises(
        ConstructionAccountingRouteSegmentV4Error, match="exact session issuer"
    ):
        route_v4.OwnedRouteSegmentStartV4(
            route_v4._ISSUER,
            start.route_segment_id,
            start.occurrence_id,
            start.route_attempt_id,
            start.recorder_id,
            start.manifest_authority_id,
            start.owner_integration_blocker_id,
        )
    with pytest.raises(
        ConstructionAccountingRouteSegmentV4Error, match="exact session issuer"
    ):
        route_v4.OwnedRouteOperationEventV4(
            route_v4._ISSUER,
            event.route_segment_start_id,
            event.boundary_id,
            event.dispatch_key,
            event.path,
            event.operation_source_symbol,
            route_v4.RouteOperationOriginV4.SOURCE_OWNED_RUNTIME,
            1,
            event.event_sequence,
            event.predecessor_chain_id,
        )
    with pytest.raises(
        ConstructionAccountingRouteSegmentV4Error, match="exact session issuer"
    ):
        route_v4.OwnedRouteSegmentTerminalV4(
            route_v4._ISSUER,
            terminal.route_segment_start_id,
            terminal.terminal_kind,
            terminal.event_ids,
            terminal.predecessor_chain_id,
            terminal.abort_reason,
        )
    with pytest.raises(
        ConstructionAccountingRouteSegmentV4Error, match="exact session issuer"
    ):
        route_v4.OwnedRouteSegmentTranscriptV4(
            route_v4._ISSUER,
            transcript.start,
            transcript.events,
            transcript.terminal,
        )


def test_failed_construction_enter_does_not_leak_active_context(
    sealed_inputs,
) -> None:
    import acfqp.construction_accounting_route_segment_v4 as route_v4

    terminal = _session(sealed_inputs, "enter-failure")
    with activate_construction_route_segment_v4(terminal):
        terminal.abort("PREPARE_TERMINAL_SESSION")
    assert route_v4._ACTIVE_ROUTE_SEGMENT_V4.get() is None

    with pytest.raises(
        ConstructionAccountingRouteSegmentV4Error, match="invalid state"
    ):
        with activate_construction_route_segment_v4(terminal):
            raise AssertionError("unreachable")
    assert route_v4._ACTIVE_ROUTE_SEGMENT_V4.get() is None

    fresh = _session(sealed_inputs, "after-enter-failure")
    with activate_construction_route_segment_v4(fresh):
        fresh.finish_construction_harness(_zero_values(fresh.authority))
        transcript = fresh.complete()
    assert transcript.terminal.terminal_kind is RouteSegmentTerminalKindV4.COMPLETED
    assert route_v4._ACTIVE_ROUTE_SEGMENT_V4.get() is None
