from __future__ import annotations

from dataclasses import replace
import hashlib
from pathlib import Path

import pytest

from acfqp import construction_accounting_route_segment_v4 as route_v4
from acfqp import construction_k7_canonical_infeasible_fallback_acquisition_v1 as acquisition_v1
from acfqp import phase3e_fallback_owned_v3 as owned_v3
from acfqp.construction_accounting_route_segment_v4 import (
    ConstructionAccountingRouteSegmentV4Error,
    OwnedEngineFallbackRouteSegmentSessionV4,
    RouteSegmentTerminalKindV4,
    activate_owned_route_segment_v4,
    verify_sealed_owned_engine_authority_v4,
)
from acfqp.domains.g2048 import G2048Kernel
from acfqp.phase3e_exact_infeasibility_durable_proof_v1 import (
    DurableExactInfeasibilityIdentityV1,
    issue_phase3e_exact_infeasibility_durable_proof_v1,
)
from acfqp.phase3e_fallback_v1 import (
    GroundFallbackOutcome,
    GroundFallbackProtocolError,
    run_ground_fallback_search_v1,
)
from acfqp.phase3e_ids import loads_canonical_json


ROOT = Path(__file__).resolve().parents[1]
CANONICAL_BUNDLE = ROOT / "artifacts" / "phase05" / "g2048"
OWNED_SOURCE = ROOT / "src" / "acfqp" / "phase3e_fallback_owned_v3.py"
LEGACY_SOURCE = ROOT / "src" / "acfqp" / "phase3e_fallback_owned_v2.py"


@pytest.fixture(scope="module")
def preexecution():
    proof_bytes = issue_phase3e_exact_infeasibility_durable_proof_v1(CANONICAL_BUNDLE)
    identity = DurableExactInfeasibilityIdentityV1.from_dict(
        loads_canonical_json(proof_bytes)["identity"]
    )
    current = acquisition_v1.build_current_canonical_fallback_identity_v1(
        CANONICAL_BUNDLE,
        build_epoch_id=identity.build_epoch_id,
        threshold_profile_id=identity.threshold_profile_id,
        reward_profile_id=identity.reward_profile_id,
        policy_class_id=identity.policy_class_id,
        complete_search_profile_id=identity.complete_search_profile_id,
    )
    proof, _verified, current = acquisition_v1._proof_document(
        proof_bytes, current_identity=current
    )
    return acquisition_v1._preexecution_candidate(
        proof, current_identity=current, cap_profile=None
    )


@pytest.fixture(scope="module")
def source_bytes() -> bytes:
    return OWNED_SOURCE.read_bytes()


@pytest.fixture(scope="module")
def authority(source_bytes: bytes):
    return verify_sealed_owned_engine_authority_v4(source_bytes)


def _session(
    preexecution,
    source_bytes,
    authority,
    suffix: str,
    *,
    cap_profile=None,
    recorder_id: str | None = None,
    search_counter_registry_id: str | None = None,
    expected_kernel=None,
    expected_query=None,
):
    cap = cap_profile or preexecution.cap_profile
    semantic_kernel = expected_kernel or G2048Kernel(2)
    semantic_query = expected_query or acquisition_v1._canonical_query(
        semantic_kernel
    )
    return OwnedEngineFallbackRouteSegmentSessionV4(
        route_segment_id=preexecution.candidate_id,
        occurrence_id=preexecution.route_context.logical_occurrence_id,
        route_attempt_id=preexecution.route_context.route_attempt_id,
        recorder_id=recorder_id or f"owned-v3-{suffix}",
        route_decision_context_id=(
            preexecution.route_context.route_decision_context_id
        ),
        decision_point_id=preexecution.decision_point.decision_point_id,
        route_decision_id=preexecution.decision.route_decision_id,
        selected_upper_id=preexecution.decision.selected_upper_id,
        query_id=preexecution.route_context.query_id,
        ground_fallback_cap_profile_id=(
            cap.ground_fallback_cap_profile_id
        ),
        search_counter_registry_id=(
            search_counter_registry_id
            or owned_v3.official_counter_registry_v1().registry_id
        ),
        expected_search_semantics=(
            route_v4.derive_owned_engine_search_semantics_v4(
                semantic_kernel,
                semantic_query,
            )
        ),
        source_member_bytes=source_bytes,
        engine_authority=authority,
        engine_binding=owned_v3.require_frozen_owned_fallback_engine_binding_v3(),
    )


def _kwargs(preexecution, *, cap_profile=None, recorder_id: str):
    return {
        "route_decision_context_id": (
            preexecution.route_context.route_decision_context_id
        ),
        "decision_point_id": preexecution.decision_point.decision_point_id,
        "route_decision_id": preexecution.decision.route_decision_id,
        "selected_upper_id": preexecution.decision.selected_upper_id,
        "route_attempt_id": preexecution.route_context.route_attempt_id,
        "query_id": preexecution.route_context.query_id,
        "cap_profile": cap_profile or preexecution.cap_profile,
        "recorder_id": recorder_id,
    }


def test_sealed_owned_engine_authority_is_exact_and_separate(
    source_bytes: bytes, authority
) -> None:
    document = authority.to_document()
    assert document["proposed_contract_version"] == "2.0.54"
    assert document["runtime_gateway_compatible"] is True
    assert document["production_owner_source_integrated"] is True
    assert document["old_v3_runner_authorizer_used"] is False
    assert document["live_path_loader_called"] is False
    assert document["formal_v7_route_authority_present"] is False
    assert document["official_execution_allowed"] is False
    assert document["bind_call_location"] == [478, 4, 478, 41]
    assert document["finish_call_location"] == [690, 4, 690, 54]
    assert document["compiled_code_fingerprints_authoritative"] is True
    assert document["ast_digests_authoritative"] is True
    assert len(document["compiled_code_fingerprints"]) == 12
    assert document["bind_directly_precedes_query_validation"] is True
    assert document["finish_directly_precedes_execution_return"] is True
    assert len(authority.boundaries) == 7
    assert verify_sealed_owned_engine_authority_v4(source_bytes).to_document() == document


def test_sealed_authority_rejects_expected_pin_override_and_default_mutation(
    monkeypatch: pytest.MonkeyPatch,
    source_bytes: bytes,
) -> None:
    altered = source_bytes + b"\n# attacker-selected source\n"
    with pytest.raises(TypeError):
        verify_sealed_owned_engine_authority_v4(
            altered,
            _expected_source_byte_count=len(altered),
            _expected_source_sha256=hashlib.sha256(altered).hexdigest(),
        )
    implementation = route_v4._FROZEN_SEALED_OWNED_ENGINE_VERIFIER_IMPL_V4
    assert implementation.__defaults__ is not None
    monkeypatch.setattr(implementation, "__defaults__", (len(altered),))
    with pytest.raises(
        ConstructionAccountingRouteSegmentV4Error,
        match="verifier implementation changed",
    ):
        verify_sealed_owned_engine_authority_v4(source_bytes)


def test_engine_validator_rejects_synchronized_dependency_and_defaults_attack(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    validator = owned_v3.require_frozen_owned_fallback_engine_binding_v3
    defaults = validator.__defaults__
    assert defaults is not None and len(defaults) == 14
    replacement = lambda frontier, _delta: frontier[0]
    runtime_globals = tuple(
        (name, replacement, replacement.__code__)
        if name == "select_constrained"
        else row
        for row in defaults[9]
        for name in (row[0],)
    )
    changed_defaults = list(defaults)
    changed_defaults[9] = runtime_globals
    monkeypatch.setattr(owned_v3, "select_constrained", replacement)
    monkeypatch.setattr(validator, "__defaults__", tuple(changed_defaults))
    with pytest.raises(
        ConstructionAccountingRouteSegmentV4Error,
        match="import seal changed",
    ):
        route_v4.verify_owned_fallback_engine_import_seal_v4(
            validator,
            owned_v3.__dict__,
        )


def test_engine_validator_rejects_whole_defaults_kwdefaults_object_and_code(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    validator = owned_v3.require_frozen_owned_fallback_engine_binding_v3
    defaults = validator.__defaults__
    assert defaults is not None
    copied_defaults = tuple(list(defaults))
    assert copied_defaults == defaults and copied_defaults is not defaults
    monkeypatch.setattr(validator, "__defaults__", copied_defaults)
    with pytest.raises(ConstructionAccountingRouteSegmentV4Error):
        route_v4.verify_owned_fallback_engine_import_seal_v4(
            validator, owned_v3.__dict__
        )
    monkeypatch.setattr(validator, "__defaults__", defaults)
    monkeypatch.setattr(validator, "__kwdefaults__", {})
    with pytest.raises(ConstructionAccountingRouteSegmentV4Error):
        route_v4.verify_owned_fallback_engine_import_seal_v4(
            validator, owned_v3.__dict__
        )
    monkeypatch.setattr(validator, "__kwdefaults__", None)
    monkeypatch.setattr(validator, "__code__", (lambda: None).__code__)
    with pytest.raises(ConstructionAccountingRouteSegmentV4Error):
        route_v4.verify_owned_fallback_engine_import_seal_v4(
            validator, owned_v3.__dict__
        )


def test_engine_validator_rejects_foreign_function_globals(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from types import FunctionType

    validator = owned_v3.require_frozen_owned_fallback_engine_binding_v3
    foreign = FunctionType(
        validator.__code__,
        dict(validator.__globals__),
        validator.__name__,
        validator.__defaults__,
        validator.__closure__,
    )
    monkeypatch.setattr(
        owned_v3,
        "require_frozen_owned_fallback_engine_binding_v3",
        foreign,
    )
    with pytest.raises(ConstructionAccountingRouteSegmentV4Error):
        route_v4.verify_owned_fallback_engine_import_seal_v4(
            foreign, owned_v3.__dict__
        )


def test_exact_search_and_all_native_values_match_reference_v1(
    preexecution, source_bytes: bytes, authority
) -> None:
    kernel = G2048Kernel(2)
    query = acquisition_v1._canonical_query(kernel)
    recorder_id = "owned-v3-exact-parity"
    kwargs = _kwargs(preexecution, recorder_id=recorder_id)
    session = _session(
        preexecution,
        source_bytes,
        authority,
        "parity",
        recorder_id=recorder_id,
    )

    with activate_owned_route_segment_v4(session):
        actual = owned_v3.run_owned_ground_fallback_search_v3(
            kernel, query, **kwargs
        )
        transcript = session.complete()
    expected = run_ground_fallback_search_v1(kernel, query, **kwargs)

    assert actual.result.to_dict() == expected.result.to_dict()
    assert actual.work_vector.to_dict() == expected.work_vector.to_dict()
    assert actual.selected_policy == expected.selected_policy
    assert actual.result.outcome is GroundFallbackOutcome.INFEASIBLE_CERTIFIED
    assert transcript.terminal.terminal_kind is RouteSegmentTerminalKindV4.COMPLETED
    assert len(transcript.events) == 208
    assert dict(transcript.values) == {
        "control.cap_checks": 56,
        "fallback.states_expanded": 8,
        "fallback.bellman_backups": 16,
        "fallback.actions_evaluated": 16,
        "fallback.ground_steps": 16,
        "fallback.outcome_rows": 96,
    }
    assert all(
        row.amount == 1
        and row.origin is route_v4.RouteOperationOriginV4.SOURCE_OWNED_RUNTIME
        and row.to_document()["origin"] == "SOURCE_OWNED_RUNTIME"
        for row in transcript.events
    )


def test_cap_exhaustion_finishes_same_owned_search_with_exact_prefix(
    preexecution, source_bytes: bytes, authority
) -> None:
    kernel = G2048Kernel(2)
    query = acquisition_v1._canonical_query(kernel)
    cap = replace(preexecution.cap_profile, max_states_expanded=7)
    session = _session(
        preexecution, source_bytes, authority, "cap", cap_profile=cap
    )

    with activate_owned_route_segment_v4(session):
        execution = owned_v3.run_owned_ground_fallback_search_v3(
            kernel,
            query,
            **_kwargs(preexecution, cap_profile=cap, recorder_id="owned-v3-cap"),
        )
        transcript = session.complete()

    assert execution.result.outcome is GroundFallbackOutcome.CAP_EXHAUSTED
    assert execution.result.search_complete is False
    assert execution.result.cap_exhausted_name == "max_states_expanded"
    assert transcript.terminal.terminal_kind is RouteSegmentTerminalKindV4.COMPLETED
    assert len(transcript.events) == 16
    assert dict(transcript.values) == {
        "control.cap_checks": 8,
        "fallback.states_expanded": 7,
        "control.cap_rejections": 1,
    }


def test_max_cap_checks_denial_is_recorded_before_counter_mutation(
    preexecution, source_bytes: bytes, authority
) -> None:
    kernel = G2048Kernel(2)
    query = acquisition_v1._canonical_query(kernel)
    cap = replace(preexecution.cap_profile, max_cap_checks=1)
    session = _session(
        preexecution,
        source_bytes,
        authority,
        "max-cap-checks",
        cap_profile=cap,
    )

    with activate_owned_route_segment_v4(session):
        execution = owned_v3.run_owned_ground_fallback_search_v3(
            kernel,
            query,
            **_kwargs(
                preexecution,
                cap_profile=cap,
                recorder_id="owned-v3-max-cap-checks",
            ),
        )
        transcript = session.complete()

    assert execution.result.outcome is GroundFallbackOutcome.CAP_EXHAUSTED
    assert execution.result.cap_exhausted_name == "max_cap_checks"
    assert len(transcript.events) == 3
    assert dict(transcript.values) == {
        "control.cap_checks": 1,
        "fallback.states_expanded": 1,
        "control.cap_rejections": 1,
    }


def test_search_without_active_session_fails_before_query_or_kernel_access(
    preexecution,
) -> None:
    class Forbidden:
        def __getattribute__(self, name):
            raise AssertionError(f"pre-bind access: {name}")

    with pytest.raises(
        ConstructionAccountingRouteSegmentV4Error,
        match="requires its exact active V4 session",
    ):
        execution = owned_v3.run_owned_ground_fallback_search_v3(
            Forbidden(),
            Forbidden(),
            **_kwargs(preexecution, recorder_id="owned-v3-no-session"),
        )


def test_second_search_bind_is_rejected_without_appending_another_event(
    preexecution, source_bytes: bytes, authority
) -> None:
    kernel = G2048Kernel(2)
    query = acquisition_v1._canonical_query(kernel)
    session = _session(preexecution, source_bytes, authority, "exact-once")
    kwargs = _kwargs(preexecution, recorder_id="owned-v3-exact-once")

    with activate_owned_route_segment_v4(session):
        owned_v3.run_owned_ground_fallback_search_v3(kernel, query, **kwargs)
        with pytest.raises(
            ConstructionAccountingRouteSegmentV4Error,
            match="search binding is invalid",
        ):
            owned_v3.run_owned_ground_fallback_search_v3(kernel, query, **kwargs)

    transcript = session.transcript
    assert transcript.terminal.terminal_kind is RouteSegmentTerminalKindV4.ABORTED
    assert transcript.terminal.abort_reason == "INVALID_SEARCH_BINDING"
    assert transcript.terminal.exact_search_finished is True
    assert len(transcript.events) == 208


def test_wrong_finish_values_abort_and_retain_only_real_events(
    preexecution,
    source_bytes: bytes,
    authority,
) -> None:
    kernel = G2048Kernel(2)
    query = acquisition_v1._canonical_query(kernel)
    cap = replace(preexecution.cap_profile, max_cap_checks=1)
    session = _session(
        preexecution, source_bytes, authority, "wrong-finish", cap_profile=cap
    )
    with pytest.raises(
        ConstructionAccountingRouteSegmentV4Error,
        match="lacks an exact finished search",
    ):
        with activate_owned_route_segment_v4(session):
            owned_v3.run_owned_ground_fallback_search_v3(
                kernel,
                query,
                **_kwargs(
                    preexecution,
                    cap_profile=cap,
                    recorder_id="owned-v3-wrong-finish",
                ),
            )
            session._bound_ledger.states_expanded += 1
            session.complete()

    assert session.transcript.terminal.abort_reason == "ABORT_LEDGER_TRANSCRIPT_DIVERGENCE"
    assert len(session.transcript.events) == 3
    assert session.transcript.values["fallback.states_expanded"] == 1


def test_double_finish_is_rejected_without_a_second_terminal_prefix(
    preexecution, source_bytes: bytes, authority
) -> None:
    kernel = G2048Kernel(2)
    query = acquisition_v1._canonical_query(kernel)
    cap = replace(preexecution.cap_profile, max_cap_checks=1)
    session = _session(
        preexecution, source_bytes, authority, "double-finish", cap_profile=cap
    )

    with activate_owned_route_segment_v4(session):
        execution = owned_v3.run_owned_ground_fallback_search_v3(
            kernel,
            query,
            **_kwargs(
                preexecution,
                cap_profile=cap,
                recorder_id="owned-v3-double-finish",
            ),
        )
        with pytest.raises(
            ConstructionAccountingRouteSegmentV4Error,
            match="search finish is invalid",
        ):
            route_v4.finish_owned_fallback_search_v4(session._bound_ledger, execution)

    assert session.transcript.terminal.abort_reason == "INVALID_SEARCH_FINISH"
    assert len(session.transcript.events) == 3


def test_event_after_finish_is_rejected_before_event_or_ledger_increment(
    preexecution, source_bytes: bytes, authority
) -> None:
    kernel = G2048Kernel(2)
    query = acquisition_v1._canonical_query(kernel)
    cap = replace(preexecution.cap_profile, max_cap_checks=1)
    session = _session(
        preexecution,
        source_bytes,
        authority,
        "event-after-finish",
        cap_profile=cap,
    )

    with activate_owned_route_segment_v4(session):
        owned_v3.run_owned_ground_fallback_search_v3(
            kernel,
            query,
            **_kwargs(
                preexecution,
                cap_profile=cap,
                recorder_id="owned-v3-event-after-finish",
            ),
        )
        before = len(session._events)
        checks_before = session._bound_ledger.cap_checks
        with pytest.raises(
            ConstructionAccountingRouteSegmentV4Error,
            match="outside its exact bound search",
        ):
            session._bound_ledger.expand_state()

    assert len(session.transcript.events) == before == 3
    assert session._bound_ledger.cap_checks == checks_before == 1
    assert session.transcript.terminal.abort_reason == "UNBOUND_LEDGER_OR_SEARCH"


def test_normal_owned_scope_exit_without_complete_aborts_finished_prefix(
    preexecution, source_bytes: bytes, authority
) -> None:
    kernel = G2048Kernel(2)
    query = acquisition_v1._canonical_query(kernel)
    cap = replace(preexecution.cap_profile, max_cap_checks=1)
    session = _session(
        preexecution,
        source_bytes,
        authority,
        "missing-complete",
        cap_profile=cap,
    )

    with pytest.raises(
        ConstructionAccountingRouteSegmentV4Error,
        match="scope exited without terminalization",
    ):
        with activate_owned_route_segment_v4(session):
            owned_v3.run_owned_ground_fallback_search_v3(
                kernel,
                query,
                **_kwargs(
                    preexecution,
                    cap_profile=cap,
                    recorder_id="owned-v3-missing-complete",
                ),
            )

    assert session.transcript.terminal.abort_reason == "INCOMPLETE_SCOPE_EXIT"
    assert session.transcript.terminal.exact_search_finished is True
    assert len(session.transcript.events) == 3


def test_duck_typed_kernel_is_rejected_by_registered_adapter() -> None:
    raw = G2048Kernel(2)

    class ExplodingKernel:
        def __getattr__(self, name):
            return getattr(raw, name)

        def step(self, state, action):
            raise RuntimeError("injected owned-v3 kernel failure")

    exploding = ExplodingKernel()
    query = acquisition_v1._canonical_query(raw)
    with pytest.raises(
        ConstructionAccountingRouteSegmentV4Error,
        match=r"registered canonical G2048Kernel\(2\)",
    ):
        route_v4.derive_owned_engine_search_semantics_v4(exploding, query)


def test_direct_gateway_spoof_aborts_without_a_fake_event(
    preexecution, source_bytes: bytes, authority
) -> None:
    session = _session(preexecution, source_bytes, authority, "gateway-spoof")
    with pytest.raises(
        ConstructionAccountingRouteSegmentV4Error,
        match="outside its exact bound search",
    ):
        with activate_owned_route_segment_v4(session):
            route_v4.emit_owned_route_operation_v4(
                "direct-fallback.state.expanded", 1
            )
    assert session.transcript.events == ()
    assert session.transcript.terminal.terminal_kind is RouteSegmentTerminalKindV4.ABORTED


@pytest.mark.parametrize("which", ("successor-byte", "legacy-source"))
def test_nonexact_owned_source_is_rejected(
    which: str, preexecution, source_bytes: bytes, authority
) -> None:
    candidate = (
        source_bytes[:-1] + bytes([source_bytes[-1] ^ 1])
        if which == "successor-byte"
        else LEGACY_SOURCE.read_bytes()
    )
    with pytest.raises(
        ConstructionAccountingRouteSegmentV4Error,
        match="differs from Contract 2.0.54",
    ):
        OwnedEngineFallbackRouteSegmentSessionV4(
            route_segment_id=preexecution.candidate_id,
            occurrence_id=preexecution.route_context.logical_occurrence_id,
            route_attempt_id=preexecution.route_context.route_attempt_id,
            recorder_id=f"owned-v3-{which}",
            route_decision_context_id=(
                preexecution.route_context.route_decision_context_id
            ),
            decision_point_id=preexecution.decision_point.decision_point_id,
            route_decision_id=preexecution.decision.route_decision_id,
            selected_upper_id=preexecution.decision.selected_upper_id,
            query_id=preexecution.route_context.query_id,
            ground_fallback_cap_profile_id=(
                preexecution.cap_profile.ground_fallback_cap_profile_id
            ),
            search_counter_registry_id=(
                owned_v3.official_counter_registry_v1().registry_id
            ),
            expected_search_semantics=route_v4.derive_owned_engine_search_semantics_v4(
                G2048Kernel(2),
                acquisition_v1._canonical_query(G2048Kernel(2)),
            ),
            source_member_bytes=candidate,
            engine_authority=authority,
            engine_binding=owned_v3.require_frozen_owned_fallback_engine_binding_v3(),
        )


def test_foreign_caller_modified_live_binding_is_rejected(
    preexecution, source_bytes: bytes, authority
) -> None:
    binding = owned_v3.require_frozen_owned_fallback_engine_binding_v3()
    foreign = binding._replace(search_entry=lambda *_args, **_kwargs: None)
    with pytest.raises(
        ConstructionAccountingRouteSegmentV4Error,
        match="foreign or unsealed live binding",
    ):
        OwnedEngineFallbackRouteSegmentSessionV4(
            route_segment_id=preexecution.candidate_id,
            occurrence_id=preexecution.route_context.logical_occurrence_id,
            route_attempt_id=preexecution.route_context.route_attempt_id,
            recorder_id="owned-v3-foreign-binding",
            route_decision_context_id=(
                preexecution.route_context.route_decision_context_id
            ),
            decision_point_id=preexecution.decision_point.decision_point_id,
            route_decision_id=preexecution.decision.route_decision_id,
            selected_upper_id=preexecution.decision.selected_upper_id,
            query_id=preexecution.route_context.query_id,
            ground_fallback_cap_profile_id=(
                preexecution.cap_profile.ground_fallback_cap_profile_id
            ),
            search_counter_registry_id=(
                owned_v3.official_counter_registry_v1().registry_id
            ),
            expected_search_semantics=route_v4.derive_owned_engine_search_semantics_v4(
                G2048Kernel(2),
                acquisition_v1._canonical_query(G2048Kernel(2)),
            ),
            source_member_bytes=source_bytes,
            engine_authority=authority,
            engine_binding=foreign,
        )


def test_forged_binding_digest_strings_do_not_replace_live_code_observation(
    preexecution, source_bytes: bytes, authority
) -> None:
    binding = owned_v3.require_frozen_owned_fallback_engine_binding_v3()
    malicious = lambda *_args, **_kwargs: None
    forged = binding._replace(
        search_entry=malicious,
        search_entry_globals=malicious.__globals__,
        search_entry_code=malicious.__code__,
        live_code_fingerprints=authority.compiled_code_fingerprints,
    )
    observed = route_v4._live_owned_engine_code_fingerprints_v4(forged)
    assert observed != forged.live_code_fingerprints
    with pytest.raises(
        ConstructionAccountingRouteSegmentV4Error,
        match="foreign or unsealed live binding",
    ):
        OwnedEngineFallbackRouteSegmentSessionV4(
            route_segment_id=preexecution.candidate_id,
            occurrence_id=preexecution.route_context.logical_occurrence_id,
            route_attempt_id=preexecution.route_context.route_attempt_id,
            recorder_id="owned-v3-forged-digest-strings",
            route_decision_context_id=(
                preexecution.route_context.route_decision_context_id
            ),
            decision_point_id=preexecution.decision_point.decision_point_id,
            route_decision_id=preexecution.decision.route_decision_id,
            selected_upper_id=preexecution.decision.selected_upper_id,
            query_id=preexecution.route_context.query_id,
            ground_fallback_cap_profile_id=(
                preexecution.cap_profile.ground_fallback_cap_profile_id
            ),
            search_counter_registry_id=(
                owned_v3.official_counter_registry_v1().registry_id
            ),
            expected_search_semantics=route_v4.derive_owned_engine_search_semantics_v4(
                G2048Kernel(2),
                acquisition_v1._canonical_query(G2048Kernel(2)),
            ),
            source_member_bytes=source_bytes,
            engine_authority=authority,
            engine_binding=forged,
        )


@pytest.mark.parametrize("target", ("ledger-method", "search-entry"))
def test_live_owner_replacement_after_session_is_rejected_before_events(
    monkeypatch: pytest.MonkeyPatch,
    target: str,
    preexecution,
    source_bytes: bytes,
    authority,
) -> None:
    session = _session(preexecution, source_bytes, authority, f"replace-{target}")
    if target == "ledger-method":
        monkeypatch.setattr(
            owned_v3._OwnedFallbackLedgerV3,
            "expand_state",
            lambda self: None,
        )
    else:
        monkeypatch.setattr(
            owned_v3,
            "run_owned_ground_fallback_search_v3",
            lambda *_args, **_kwargs: None,
        )

    with pytest.raises(
        ConstructionAccountingRouteSegmentV4Error,
        match="live binding changed",
    ):
        with activate_owned_route_segment_v4(session):
            raise AssertionError("unreachable")
    assert session.transcript.events == ()
    assert session.transcript.terminal.terminal_kind is RouteSegmentTerminalKindV4.ABORTED


def test_v4_bind_replacement_is_rejected_before_any_owned_event(
    monkeypatch: pytest.MonkeyPatch,
    preexecution,
    source_bytes: bytes,
    authority,
) -> None:
    session = _session(preexecution, source_bytes, authority, "replace-bind")
    kernel = G2048Kernel(2)
    query = acquisition_v1._canonical_query(kernel)
    monkeypatch.setattr(
        route_v4,
        "bind_owned_fallback_search_v4",
        lambda _ledger: None,
    )
    with pytest.raises(
        ConstructionAccountingRouteSegmentV4Error,
        match="search binding is invalid",
    ):
        with activate_owned_route_segment_v4(session):
            owned_v3.run_owned_ground_fallback_search_v3(
                kernel,
                query,
                **_kwargs(preexecution, recorder_id="owned-v3-replace-bind"),
            )
    assert session.transcript.events == ()


def test_v4_gateway_replacement_is_rejected_before_first_counter_mutation(
    monkeypatch: pytest.MonkeyPatch,
    preexecution,
    source_bytes: bytes,
    authority,
) -> None:
    session = _session(preexecution, source_bytes, authority, "replace-gateway")
    kernel = G2048Kernel(2)
    query = acquisition_v1._canonical_query(kernel)
    monkeypatch.setattr(
        route_v4,
        "emit_owned_route_operation_v4",
        lambda _dispatch_key, _amount=1: route_v4.OWNED_ROUTE_EVENT_ACK_V4,
    )
    with pytest.raises(
        ConstructionAccountingRouteSegmentV4Error,
        match="bypassed the frozen gateway",
    ):
        with activate_owned_route_segment_v4(session):
            owned_v3.run_owned_ground_fallback_search_v3(
                kernel,
                query,
                **_kwargs(preexecution, recorder_id="owned-v3-replace-gateway"),
            )
    assert session.transcript.events == ()
    assert session._bound_ledger.cap_checks == 0


def test_v4_finish_replacement_aborts_after_retaining_exact_finished_prefix(
    monkeypatch: pytest.MonkeyPatch,
    preexecution,
    source_bytes: bytes,
    authority,
) -> None:
    cap = replace(preexecution.cap_profile, max_cap_checks=1)
    session = _session(
        preexecution, source_bytes, authority, "replace-finish", cap_profile=cap
    )
    kernel = G2048Kernel(2)
    query = acquisition_v1._canonical_query(kernel)
    monkeypatch.setattr(
        route_v4,
        "finish_owned_fallback_search_v4",
        lambda _ledger, _execution: None,
    )
    with pytest.raises(
        ConstructionAccountingRouteSegmentV4Error,
        match="search finish is invalid",
    ):
        with activate_owned_route_segment_v4(session):
            owned_v3.run_owned_ground_fallback_search_v3(
                kernel,
                query,
                **_kwargs(
                    preexecution,
                    cap_profile=cap,
                    recorder_id="owned-v3-replace-finish",
                ),
            )
    assert len(session.transcript.events) == 3
    assert session.transcript.terminal.abort_reason == "INVALID_SEARCH_FINISH"


def test_readable_node_issuer_cannot_mint_an_owned_engine_start(
    preexecution, source_bytes: bytes, authority
) -> None:
    session = _session(preexecution, source_bytes, authority, "node-issuer")
    start = session.start
    with pytest.raises(
        ConstructionAccountingRouteSegmentV4Error,
        match="exact session issuer",
    ):
        route_v4.OwnedEngineRouteSegmentStartV4(
            route_v4._ISSUER,
            start.route_segment_id,
            start.occurrence_id,
            start.route_attempt_id,
            start.recorder_id,
            start.owned_engine_authority_id,
            start.counter_registry_id,
            start.stage_profile_id,
            start.route_decision_context_id,
            start.decision_point_id,
            start.route_decision_id,
            start.selected_upper_id,
            start.query_id,
            start.ground_fallback_cap_profile_id,
            start.search_counter_registry_id,
            start.search_semantics,
        )


def test_object_new_or_copied_mint_cannot_forge_owned_start(
    preexecution, source_bytes: bytes, authority
) -> None:
    start = _session(preexecution, source_bytes, authority, "object-new").start
    forged = object.__new__(route_v4.OwnedEngineRouteSegmentStartV4)
    for field_name in route_v4.OwnedEngineRouteSegmentStartV4.__slots__:
        object.__setattr__(forged, field_name, getattr(start, field_name))
    with pytest.raises(
        ConstructionAccountingRouteSegmentV4Error,
        match="retained owner mint",
    ):
        forged.to_document()


def test_mutated_minted_start_is_rejected_before_activation(
    preexecution, source_bytes: bytes, authority
) -> None:
    session = _session(preexecution, source_bytes, authority, "mutated-start")
    object.__setattr__(session._start, "query_id", "f" * 64)
    with pytest.raises(
        ConstructionAccountingRouteSegmentV4Error,
        match="retained owner mint",
    ):
        with activate_owned_route_segment_v4(session):
            raise AssertionError("unreachable")


def test_select_constrained_replacement_cannot_issue_completed_transcript(
    monkeypatch: pytest.MonkeyPatch,
    preexecution,
    source_bytes: bytes,
    authority,
) -> None:
    session = _session(preexecution, source_bytes, authority, "select-attack")
    kernel = G2048Kernel(2)
    query = acquisition_v1._canonical_query(kernel)
    with pytest.raises(
        ConstructionAccountingRouteSegmentV4Error,
        match="runtime dependency 'select_constrained' changed",
    ):
        with activate_owned_route_segment_v4(session):
            monkeypatch.setattr(
                owned_v3,
                "select_constrained",
                lambda frontier, _delta: frontier[0],
            )
            owned_v3.run_owned_ground_fallback_search_v3(
                kernel,
                query,
                **_kwargs(preexecution, recorder_id="owned-v3-select-attack"),
            )
    transcript = session.transcript
    assert transcript.terminal.terminal_kind is RouteSegmentTerminalKindV4.ABORTED
    assert transcript.events == ()


@pytest.mark.parametrize(
    ("field_name", "wrong_value"),
    (
        ("route_decision_context_id", "a" * 64),
        ("decision_point_id", "b" * 64),
        ("route_decision_id", "c" * 64),
        ("selected_upper_id", "d" * 64),
        ("route_attempt_id", "e" * 64),
        ("query_id", "f" * 64),
        ("recorder_id", "wrong-owned-recorder"),
    ),
)
def test_search_identity_splice_is_rejected_before_first_event(
    field_name: str,
    wrong_value: str,
    preexecution,
    source_bytes: bytes,
    authority,
) -> None:
    session = _session(preexecution, source_bytes, authority, "identity-splice")
    kernel = G2048Kernel(2)
    query = acquisition_v1._canonical_query(kernel)
    kwargs = _kwargs(preexecution, recorder_id="owned-v3-identity-splice")
    kwargs[field_name] = wrong_value
    with pytest.raises(
        ConstructionAccountingRouteSegmentV4Error,
        match="identities differ from its start",
    ):
        with activate_owned_route_segment_v4(session):
            owned_v3.run_owned_ground_fallback_search_v3(kernel, query, **kwargs)
    assert session.transcript.events == ()
    assert session.transcript.terminal.abort_reason == "SEARCH_IDENTITY_MISMATCH"


def test_search_cap_splice_is_rejected_before_first_event(
    preexecution, source_bytes: bytes, authority
) -> None:
    session = _session(preexecution, source_bytes, authority, "cap-splice")
    kernel = G2048Kernel(2)
    query = acquisition_v1._canonical_query(kernel)
    cap = replace(preexecution.cap_profile, max_states_expanded=7)
    with pytest.raises(
        ConstructionAccountingRouteSegmentV4Error,
        match="cap/registry/zero-ledger binding changed",
    ):
        with activate_owned_route_segment_v4(session):
            owned_v3.run_owned_ground_fallback_search_v3(
                kernel,
                query,
                **_kwargs(
                    preexecution,
                    cap_profile=cap,
                    recorder_id="owned-v3-cap-splice",
                ),
            )
    assert session.transcript.events == ()


def test_actual_query_threshold_semantics_reject_original_caller_label(
    preexecution, source_bytes: bytes, authority
) -> None:
    kernel = G2048Kernel(2)
    canonical_query = acquisition_v1._canonical_query(kernel)
    altered_query = replace(canonical_query, delta=owned_v3.Fraction(1, 10))
    session = _session(
        preexecution,
        source_bytes,
        authority,
        "query-semantics-splice",
        expected_kernel=kernel,
        expected_query=canonical_query,
    )
    start_document = session.start.to_document()
    assert start_document["query_id"] == preexecution.route_context.query_id
    assert start_document["derived_query_id"] != start_document["query_id"]
    assert start_document["search_semantics_id"]
    with pytest.raises(
        ConstructionAccountingRouteSegmentV4Error,
        match="actual kernel/query semantics differ",
    ):
        with activate_owned_route_segment_v4(session):
            owned_v3.run_owned_ground_fallback_search_v3(
                kernel,
                altered_query,
                **_kwargs(
                    preexecution,
                    recorder_id="owned-v3-query-semantics-splice",
                ),
            )
    assert session.transcript.events == ()
    assert session.transcript.terminal.abort_reason == "SEARCH_SEMANTICS_MISMATCH"


def test_actual_kernel_semantics_reject_original_caller_label(
    preexecution, source_bytes: bytes, authority
) -> None:
    canonical_kernel = G2048Kernel(2)
    canonical_query = acquisition_v1._canonical_query(canonical_kernel)
    session = _session(
        preexecution,
        source_bytes,
        authority,
        "kernel-semantics-splice",
        expected_kernel=canonical_kernel,
        expected_query=canonical_query,
    )
    with pytest.raises(
        ConstructionAccountingRouteSegmentV4Error,
        match="actual search semantics are unavailable",
    ):
        with activate_owned_route_segment_v4(session):
            owned_v3.run_owned_ground_fallback_search_v3(
                G2048Kernel(3),
                canonical_query,
                **_kwargs(
                    preexecution,
                    recorder_id="owned-v3-kernel-semantics-splice",
                ),
            )
    assert session.transcript.events == ()
    assert (
        session.transcript.terminal.abort_reason
        == "SEARCH_SEMANTICS_DERIVATION_INVALID"
    )


def test_private_adjacency_rewrite_fails_before_first_owned_event(
    monkeypatch: pytest.MonkeyPatch,
    preexecution,
    source_bytes: bytes,
    authority,
) -> None:
    session = _session(
        preexecution,
        source_bytes,
        authority,
        "adjacency-rewrite",
    )

    def rewritten_adjacency(self, first, second):
        return first != second

    monkeypatch.setattr(G2048Kernel, "_adjacent", rewritten_adjacency)
    with pytest.raises(
        ConstructionAccountingRouteSegmentV4Error,
        match="live G2048 transition closure changed",
    ):
        with activate_owned_route_segment_v4(session):
            pass
    assert session.transcript.events == ()
    assert (
        session.transcript.terminal.abort_reason
        == "LIVE_G2048_TRANSITION_CLOSURE_CHANGED"
    )


def test_actions_and_fingerprint_helper_synchronized_rewrite_fails_before_event(
    monkeypatch: pytest.MonkeyPatch,
    preexecution,
    source_bytes: bytes,
    authority,
) -> None:
    session = _session(
        preexecution,
        source_bytes,
        authority,
        "actions-fingerprint-rewrite",
    )
    original_actions = G2048Kernel.actions
    original_fingerprint = route_v4._normalized_recursive_code_fingerprint_v4

    def rewritten_actions(self, state):
        return original_actions(self, state)

    def masking_fingerprint(code):
        if code is rewritten_actions.__code__:
            return original_fingerprint(original_actions.__code__)
        return original_fingerprint(code)

    monkeypatch.setattr(G2048Kernel, "actions", rewritten_actions)
    monkeypatch.setattr(
        route_v4,
        "_normalized_recursive_code_fingerprint_v4",
        masking_fingerprint,
    )
    with pytest.raises(
        ConstructionAccountingRouteSegmentV4Error,
        match="live G2048 transition closure changed",
    ):
        with activate_owned_route_segment_v4(session):
            pass
    assert session.transcript.events == ()
    assert (
        session.transcript.terminal.abort_reason
        == "LIVE_G2048_TRANSITION_CLOSURE_CHANGED"
    )


def test_stateful_getattribute_rewrite_fails_before_first_owned_event(
    monkeypatch: pytest.MonkeyPatch,
    preexecution,
    source_bytes: bytes,
    authority,
) -> None:
    kernel = G2048Kernel(2)
    query = acquisition_v1._canonical_query(kernel)
    session = _session(
        preexecution,
        source_bytes,
        authority,
        "stateful-getattribute-rewrite",
        expected_kernel=kernel,
        expected_query=query,
    )
    original_getattribute = object.__getattribute__
    action_reads = 0

    def stateful_getattribute(self, name):
        nonlocal action_reads
        if name == "actions":
            action_reads += 1
            if action_reads > 1:
                return lambda _state: ()
        return original_getattribute(self, name)

    monkeypatch.setattr(
        G2048Kernel,
        "__getattribute__",
        stateful_getattribute,
        raising=False,
    )
    with pytest.raises(
        ConstructionAccountingRouteSegmentV4Error,
        match="live G2048 transition closure changed",
    ):
        with activate_owned_route_segment_v4(session):
            owned_v3.run_owned_ground_fallback_search_v3(
                kernel,
                query,
                **_kwargs(
                    preexecution,
                    recorder_id="owned-v3-stateful-getattribute-rewrite",
                ),
            )
    assert action_reads == 0
    assert session.transcript.events == ()
    assert (
        session.transcript.terminal.abort_reason
        == "LIVE_G2048_TRANSITION_CLOSURE_CHANGED"
    )


def test_search_registry_splice_is_rejected_before_first_event(
    preexecution, source_bytes: bytes, authority
) -> None:
    session = _session(
        preexecution,
        source_bytes,
        authority,
        "registry-splice",
        search_counter_registry_id="a" * 64,
    )
    kernel = G2048Kernel(2)
    query = acquisition_v1._canonical_query(kernel)
    with pytest.raises(
        ConstructionAccountingRouteSegmentV4Error,
        match="cap/registry/zero-ledger binding changed",
    ):
        with activate_owned_route_segment_v4(session):
            owned_v3.run_owned_ground_fallback_search_v3(
                kernel,
                query,
                **_kwargs(preexecution, recorder_id="owned-v3-registry-splice"),
            )
    assert session.transcript.events == ()


@pytest.mark.parametrize(
    ("cap_name", "cap_changes"),
    (
        (
            "max_actions_evaluated",
            {"max_actions_evaluated": 1, "max_ground_steps": 1},
        ),
        ("max_ground_steps", {"max_ground_steps": 1}),
        ("max_outcome_rows", {"max_outcome_rows": 6}),
        ("max_bellman_backups", {"max_bellman_backups": 1}),
        ("max_composed_candidates", {"max_composed_candidates": 1}),
    ),
)
def test_every_solver_cap_returns_exact_owned_positive_prefix(
    cap_name: str,
    cap_changes: dict[str, int],
    preexecution,
    source_bytes: bytes,
    authority,
) -> None:
    cap = replace(preexecution.cap_profile, **cap_changes)
    recorder_id = f"owned-v3-cap-{cap_name}"
    session = _session(
        preexecution,
        source_bytes,
        authority,
        f"cap-{cap_name}",
        cap_profile=cap,
        recorder_id=recorder_id,
    )
    kernel = G2048Kernel(2)
    query = acquisition_v1._canonical_query(kernel)
    with activate_owned_route_segment_v4(session):
        execution = owned_v3.run_owned_ground_fallback_search_v3(
            kernel,
            query,
            **_kwargs(
                preexecution,
                cap_profile=cap,
                recorder_id=recorder_id,
            ),
        )
        transcript = session.complete()
    assert execution.result.outcome is GroundFallbackOutcome.CAP_EXHAUSTED
    assert execution.result.cap_exhausted_name == cap_name
    assert transcript.terminal.terminal_kind is RouteSegmentTerminalKindV4.COMPLETED
    for path, value in transcript.values.items():
        assert execution.work_vector.values[path] == value
    assert (
        execution.result.composed_candidate_count
        == execution.work_vector.values["fallback.bellman_backups"]
    )


def test_protocol_outcome_overflow_reconciles_partial_vector_and_transcript(
    preexecution, source_bytes: bytes, authority
) -> None:
    cap = replace(
        preexecution.cap_profile,
        max_positive_outcomes_per_step=5,
    )
    recorder_id = "owned-v3-protocol-overflow"
    session = _session(
        preexecution,
        source_bytes,
        authority,
        "protocol-overflow",
        cap_profile=cap,
        recorder_id=recorder_id,
    )
    kernel = G2048Kernel(2)
    query = acquisition_v1._canonical_query(kernel)
    with pytest.raises(GroundFallbackProtocolError) as raised:
        with activate_owned_route_segment_v4(session):
            owned_v3.run_owned_ground_fallback_search_v3(
                kernel,
                query,
                **_kwargs(
                    preexecution,
                    cap_profile=cap,
                    recorder_id=recorder_id,
                ),
            )
    partial = raised.value.partial_work_vector
    assert partial is not None
    transcript = session.transcript
    assert transcript.terminal.terminal_kind is RouteSegmentTerminalKindV4.ABORTED
    for path, value in transcript.values.items():
        assert partial.values[path] == value
    assert partial.values["fallback.bellman_backups"] == 1
    assert transcript.values["fallback.outcome_rows"] == 6


def test_subclassed_kernel_is_rejected_by_registered_adapter() -> None:
    raw = G2048Kernel(2)

    class SubclassedKernel(G2048Kernel):
        pass

    subclassed = SubclassedKernel(2)
    query = acquisition_v1._canonical_query(raw)
    with pytest.raises(
        ConstructionAccountingRouteSegmentV4Error,
        match=r"registered canonical G2048Kernel\(2\)",
    ):
        route_v4.derive_owned_engine_search_semantics_v4(subclassed, query)


def test_work_materialization_exception_retains_full_unfinished_prefix(
    preexecution, source_bytes: bytes, authority
) -> None:
    official = owned_v3.official_counter_registry_v1()

    class ExplodingRegistry:
        @property
        def registry_id(self):
            return official.registry_id

        @property
        def required_paths(self):
            return official.required_paths

        @property
        def by_path(self):
            return official.by_path

        def validate_official_catalogue(self):
            return None

        def materialize(self, **_kwargs):
            raise RuntimeError("injected WorkVector materialization failure")

    session = _session(preexecution, source_bytes, authority, "work-error")
    kernel = G2048Kernel(2)
    query = acquisition_v1._canonical_query(kernel)
    with pytest.raises(RuntimeError, match="WorkVector materialization failure"):
        with activate_owned_route_segment_v4(session):
            owned_v3.run_owned_ground_fallback_search_v3(
                kernel,
                query,
                **_kwargs(preexecution, recorder_id="owned-v3-work-error"),
                registry=ExplodingRegistry(),
            )
    transcript = session.transcript
    assert transcript.terminal.terminal_kind is RouteSegmentTerminalKindV4.ABORTED
    assert transcript.terminal.exact_search_finished is False
    assert len(transcript.events) == 208


def test_composed_candidate_divergence_prevents_completion(
    preexecution, source_bytes: bytes, authority
) -> None:
    cap = replace(preexecution.cap_profile, max_cap_checks=1)
    recorder_id = "owned-v3-composed-divergence"
    session = _session(
        preexecution,
        source_bytes,
        authority,
        "composed-divergence",
        cap_profile=cap,
        recorder_id=recorder_id,
    )
    kernel = G2048Kernel(2)
    query = acquisition_v1._canonical_query(kernel)
    with pytest.raises(
        ConstructionAccountingRouteSegmentV4Error,
        match="candidate/backup equality changed",
    ):
        with activate_owned_route_segment_v4(session):
            owned_v3.run_owned_ground_fallback_search_v3(
                kernel,
                query,
                **_kwargs(
                    preexecution,
                    cap_profile=cap,
                    recorder_id=recorder_id,
                ),
            )
            session._bound_ledger.composed_candidates += 1
            session.complete()
    assert session.transcript.terminal.terminal_kind is RouteSegmentTerminalKindV4.ABORTED


def test_finished_result_identity_mutation_prevents_completion(
    preexecution, source_bytes: bytes, authority
) -> None:
    cap = replace(preexecution.cap_profile, max_cap_checks=1)
    recorder_id = "owned-v3-result-identity-divergence"
    session = _session(
        preexecution,
        source_bytes,
        authority,
        "result-identity-divergence",
        cap_profile=cap,
        recorder_id=recorder_id,
    )
    kernel = G2048Kernel(2)
    query = acquisition_v1._canonical_query(kernel)
    with pytest.raises(
        ConstructionAccountingRouteSegmentV4Error,
        match="result/work identities differ from its start",
    ):
        with activate_owned_route_segment_v4(session):
            execution = owned_v3.run_owned_ground_fallback_search_v3(
                kernel,
                query,
                **_kwargs(
                    preexecution,
                    cap_profile=cap,
                    recorder_id=recorder_id,
                ),
            )
            object.__setattr__(execution.result, "query_id", "f" * 64)
            session.complete()
    assert session.transcript.terminal.abort_reason == "RESULT_WORK_BINDING_MISMATCH"


def test_published_finished_binding_rejects_cap_policy_result_and_work_replacement(
    preexecution, source_bytes: bytes, authority
) -> None:
    cap = replace(preexecution.cap_profile, max_states_expanded=7)
    recorder_id = "owned-v3-published-binding-cap"
    session = _session(
        preexecution,
        source_bytes,
        authority,
        "published-binding-cap",
        cap_profile=cap,
        recorder_id=recorder_id,
    )
    kernel = G2048Kernel(2)
    query = acquisition_v1._canonical_query(kernel)
    with activate_owned_route_segment_v4(session):
        execution = owned_v3.run_owned_ground_fallback_search_v3(
            kernel,
            query,
            **_kwargs(
                preexecution,
                cap_profile=cap,
                recorder_id=recorder_id,
            ),
        )
        transcript = session.complete()
    binding = transcript.terminal.finished_execution_binding
    assert binding is not None
    assert transcript.to_document()["finished_execution_binding_id"] == binding.binding_id
    assert (
        route_v4.verify_owned_engine_finished_execution_binding_v4(
            binding,
            execution,
        )
        is binding
    )

    altered_cap_result = replace(
        execution.result,
        cap_exhausted_name="max_ground_steps",
    )
    altered_cap_execution = replace(execution, result=altered_cap_result)
    with pytest.raises(
        ConstructionAccountingRouteSegmentV4Error,
        match="differs from the transcript binding",
    ):
        route_v4.verify_owned_engine_finished_execution_binding_v4(
            binding,
            altered_cap_execution,
        )

    probability, state = next(
        iter(owned_v3.query_initial_distribution(kernel, query))
    )
    assert probability > 0
    action = kernel.actions(state)[0]
    altered_policy_execution = replace(execution)
    object.__setattr__(
        altered_policy_execution,
        "selected_policy",
        owned_v3.FiniteHorizonPolicy.from_mapping({(1, state): action}),
    )
    with pytest.raises(
        ConstructionAccountingRouteSegmentV4Error,
        match="differs from the transcript binding",
    ):
        route_v4.verify_owned_engine_finished_execution_binding_v4(
            binding,
            altered_policy_execution,
        )

    altered_result_execution = replace(
        execution,
        result=replace(
            execution.result,
            composed_candidate_count=execution.result.composed_candidate_count + 1,
        ),
    )
    with pytest.raises(
        ConstructionAccountingRouteSegmentV4Error,
        match="differs from the transcript binding",
    ):
        route_v4.verify_owned_engine_finished_execution_binding_v4(
            binding,
            altered_result_execution,
        )

    changed_path = "io.output_bytes"
    changed_records = tuple(
        replace(record, value=record.value + 1)
        if record.path == changed_path
        else record
        for record in execution.work_vector.records
    )
    assert changed_records != execution.work_vector.records
    altered_work = replace(
        execution.work_vector,
        records=changed_records,
    )
    altered_work_result = replace(
        execution.result,
        work_vector_id=altered_work.work_vector_id,
    )
    altered_work_execution = replace(
        execution,
        result=altered_work_result,
        work_vector=altered_work,
    )
    with pytest.raises(
        ConstructionAccountingRouteSegmentV4Error,
        match="differs from the transcript binding",
    ):
        route_v4.verify_owned_engine_finished_execution_binding_v4(
            binding,
            altered_work_execution,
        )

    altered_provenance_execution = replace(
        execution,
        trusted_provenance=object(),
    )
    with pytest.raises(
        ConstructionAccountingRouteSegmentV4Error,
        match="differs from the transcript binding",
    ):
        route_v4.verify_owned_engine_finished_execution_binding_v4(
            binding,
            altered_provenance_execution,
        )


def test_published_finished_binding_rejects_infeasible_frontier_replacement(
    preexecution, source_bytes: bytes, authority
) -> None:
    recorder_id = "owned-v3-published-binding-frontier"
    session = _session(
        preexecution,
        source_bytes,
        authority,
        "published-binding-frontier",
        recorder_id=recorder_id,
    )
    kernel = G2048Kernel(2)
    query = acquisition_v1._canonical_query(kernel)
    with activate_owned_route_segment_v4(session):
        execution = owned_v3.run_owned_ground_fallback_search_v3(
            kernel,
            query,
            **_kwargs(preexecution, recorder_id=recorder_id),
        )
        transcript = session.complete()
    binding = transcript.terminal.finished_execution_binding
    assert binding is not None
    original_point = execution.result.frontier[0]
    first_row = original_point.policy_signature[0]
    altered_action_id = "f" * 64 if first_row[2] != "f" * 64 else "e" * 64
    changed = replace(
        original_point,
        policy_signature=(
            (first_row[0], first_row[1], altered_action_id),
            *original_point.policy_signature[1:],
        ),
    )
    altered_frontier = tuple(
        sorted(
            (changed, *execution.result.frontier[1:]),
            key=lambda point: (
                point.failure_probability,
                -point.expected_reward,
                point.policy_signature,
            ),
        )
    )
    altered_result = replace(execution.result, frontier=altered_frontier)
    altered_execution = replace(execution, result=altered_result)
    with pytest.raises(
        ConstructionAccountingRouteSegmentV4Error,
        match="differs from the transcript binding",
    ):
        route_v4.verify_owned_engine_finished_execution_binding_v4(
            binding,
            altered_execution,
        )


def test_public_finished_verifier_rejects_material_helper_replacement(
    monkeypatch: pytest.MonkeyPatch,
    preexecution,
    source_bytes: bytes,
    authority,
) -> None:
    cap = replace(preexecution.cap_profile, max_states_expanded=7)
    recorder_id = "owned-v3-finished-helper-replacement"
    session = _session(
        preexecution,
        source_bytes,
        authority,
        "finished-helper-replacement",
        cap_profile=cap,
        recorder_id=recorder_id,
    )
    kernel = G2048Kernel(2)
    query = acquisition_v1._canonical_query(kernel)
    with activate_owned_route_segment_v4(session):
        execution = owned_v3.run_owned_ground_fallback_search_v3(
            kernel,
            query,
            **_kwargs(
                preexecution,
                cap_profile=cap,
                recorder_id=recorder_id,
            ),
        )
        transcript = session.complete()
    binding = transcript.terminal.finished_execution_binding
    assert binding is not None
    monkeypatch.setattr(
        route_v4,
        "_finished_execution_material_v4",
        lambda _execution, _policy: {},
    )
    with pytest.raises(
        ConstructionAccountingRouteSegmentV4Error,
        match="material helper or dependency changed",
    ):
        route_v4.verify_owned_engine_finished_execution_binding_v4(
            binding,
            execution,
        )
