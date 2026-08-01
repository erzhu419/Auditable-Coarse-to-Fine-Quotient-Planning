from __future__ import annotations

import hashlib
import inspect
from threading import Thread

import pytest

from acfqp.phase3e_ids import (
    V075_K7_ATTEMPT_PROCESS_LAUNCH_EVENT_V1_DOMAIN,
    canonical_json_bytes,
    loads_canonical_json,
)
from acfqp import campaign_v1 as campaign
from acfqp import routing_v1 as routing
from acfqp import v075_k7_atomic_pidfd_runtime_v1 as runtime_v1
from acfqp import v075_k7_attempt_process_executor_v1 as executor_v1
from acfqp import v075_k7_attempt_process_sink_v1 as sink_v1
from acfqp import v075_k7_attempt_process_supervisor_v1 as supervisor_v1
from acfqp import v075_k7_parent_owned_successor_ipc_v1 as successor_v1
from acfqp import v075_k7_root_cap_accounted_sealed_ipc_v1 as accounted_v1
from acfqp import v075_public_campaign_authority_v1 as public_authority_v1


def _id(label: str) -> str:
    return hashlib.sha256(
        b"acfqp:k7-attempt-process-supervisor-test:v1\x00"
        + label.encode("ascii")
    ).hexdigest()


def _request(label: str):
    accounted_profile = (
        accounted_v1.freeze_v075_k7_root_cap_accounted_sealed_ipc_profile_v1(
            timeout_milliseconds=5_000
        )
    )
    successor_profile = (
        successor_v1.freeze_v075_k7_parent_owned_successor_ipc_profile_v1(
            accounted_profile=accounted_profile
        )
    )
    signer_registry = public_authority_v1.V075TrustedSignerRegistryV1(
        public_authority_v1.V075RSAPublicVerificationKeyV1(
            "CAMPAIGN_AUTHORITY", (1 << 2047) + 1
        ),
        public_authority_v1.V075RSAPublicVerificationKeyV1(
            "OBSERVER_EVIDENCE", (1 << 2047) + 3
        ),
    )
    occurrence = campaign.LogicalOccurrenceV1(
        _id(f"workload-{label}"),
        _id(f"protocol-{label}"),
        1,
        _id(f"structural-{label}"),
        _id(f"query-{label}"),
        _id(f"plan-{label}"),
        _id(f"threshold-{label}"),
        _id(f"epoch-{label}"),
        _id(f"rebuild-{label}"),
    )
    attempt = campaign.RouteAttemptV1.initial(occurrence)
    context = routing.RouteDecisionContextV1(
        _id(f"preregistration-{label}"),
        occurrence.protocol_id,
        accounted_profile.comparison_profile_id,
        accounted_profile.counter_registry_id,
        occurrence.structural_id,
        occurrence.query_id,
        occurrence.selected_plan_id,
        occurrence.threshold_profile_id,
        attempt.build_epoch_id,
        occurrence.logical_occurrence_id,
        attempt.route_attempt_id,
    )
    decision = routing.DecisionPointV1(
        context.route_decision_context_id,
        1,
        _id(f"frontier-{label}"),
        _id(f"causal-{label}"),
        _id(f"prefix-{label}"),
    )
    transaction = routing.TransactionV1(
        occurrence.logical_occurrence_id,
        attempt.route_attempt_id,
        decision.decision_point_id,
        1,
        decision.frontier_snapshot_id,
        _id(f"cap-{label}"),
    )
    route = (
        accounted_v1.freeze_v075_k7_root_cap_accounted_sealed_route_identity_v1(
            profile=accounted_profile,
            logical_occurrence=occurrence,
            route_attempt=attempt,
            route_context=context,
            decision_point=decision,
            transaction=transaction,
        )
    )
    return successor_v1.freeze_v075_k7_parent_owned_successor_request_v1(
        profile=successor_profile,
        route_identity=route,
        signer_registry=signer_registry,
        opaque_environment_commitment_id=_id(f"opaque-{label}"),
        sealed_secret_commitment_id=_id(f"secret-{label}"),
        session_external_id=_id(f"session-{label}"),
        request_nonce=_id(f"nonce-{label}"),
        scientific_occurrence_id=_id(f"science-{label}"),
        schedule_id=_id(f"schedule-{label}"),
    )


@pytest.fixture
def test_authority():
    return supervisor_v1._issue_v075_k7_attempt_process_test_authority_v1()


@pytest.fixture(scope="module")
def shared_request():
    return _request("shared")


def _start_for_testing(authority):
    return supervisor_v1._start_v075_k7_attempt_process_supervisor_session_for_testing_v1(
        authority
    )


def _inject_for_testing(session, authority) -> None:
    supervisor_v1._inject_v075_k7_attempt_process_launch_for_testing_v1(
        session=session,
        authority=authority,
    )


def _bound_session(request, authority):
    session = _start_for_testing(authority)
    execution = session.bind_request(request)
    return session, request, execution


def test_inactive_hook_is_false_and_accepts_no_totals() -> None:
    assert sink_v1.record_v075_k7_attempt_process_launch_v1() is False
    assert len(
        inspect.signature(
            sink_v1.record_v075_k7_attempt_process_launch_v1
        ).parameters
    ) == 0
    with pytest.raises(TypeError):
        sink_v1.record_v075_k7_attempt_process_launch_v1(1)  # type: ignore[call-arg]


def test_zero_prelaunch_and_identity_bind_failure_are_immutable_raw_prefixes(
    test_authority,
    shared_request,
) -> None:
    session, _request_value, execution = _bound_session(
        shared_request, test_authority
    )
    journal = session.close(
        supervisor_v1.AttemptProcessCloseKindV1.PRELAUNCH_FAILURE
    )
    assert journal.observed_launch_count == 0
    assert journal.launch_edge_lower_bound == 0
    assert journal.execution_document["process_execution_id"] == execution.execution_id
    assert journal.to_document()["raw_launch_event_list_empty"] is True
    assert journal.to_document()["attempt_wide_raw_process_evidence"] is False
    assert journal.to_document()[
        "registered_prebind_through_parent_payload_raw_prefix"
    ] is True
    verification = (
        supervisor_v1.verify_v075_k7_attempt_process_raw_journal_bytes_v1(
            raw=journal.canonical_bytes,
            expected=journal,
        )
    )
    assert verification.observed_launch_count == 0
    assert verification.to_document()["formal_counter_record_authorized"] is False

    unbound = _start_for_testing(test_authority)
    unbound_journal = unbound.close(
        supervisor_v1.AttemptProcessCloseKindV1.IDENTITY_BIND_FAILURE
    )
    assert unbound_journal.execution_document is None
    assert unbound_journal.observed_launch_count == 0


def test_nested_duplicate_and_foreign_call_sites_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
    test_authority,
    shared_request,
) -> None:
    session, _request_value, _execution = _bound_session(
        shared_request, test_authority
    )
    with session.activate_process_sink():
        with pytest.raises(
            sink_v1.V075K7AttemptProcessSinkV1Error, match="foreign call site"
        ):
            sink_v1.record_v075_k7_attempt_process_launch_v1()

        def same_name_spoof():
            return sink_v1.record_v075_k7_attempt_process_launch_v1()

        same_name_spoof.__name__ = "run_v075_k7_atomic_pidfd_runtime_v1"
        same_name_spoof.__module__ = runtime_v1.__name__
        with pytest.raises(
            sink_v1.V075K7AttemptProcessSinkV1Error, match="foreign call site"
        ):
            same_name_spoof()
        with pytest.raises(
            sink_v1.V075K7AttemptProcessSinkV1Error, match="nested"
        ):
            with session.activate_process_sink():
                pass
        original_runtime = runtime_v1.run_v075_k7_atomic_pidfd_runtime_v1

        def monkeypatched_runtime():
            return sink_v1.record_v075_k7_attempt_process_launch_v1()

        monkeypatch.setattr(
            runtime_v1,
            "run_v075_k7_atomic_pidfd_runtime_v1",
            monkeypatched_runtime,
        )
        assert sink_v1._PINNED_RUNTIME_CALLSITE.function is original_runtime
        with pytest.raises(
            sink_v1.V075K7AttemptProcessSinkV1Error,
            match="foreign call site",
        ):
            monkeypatched_runtime()
        _inject_for_testing(session, test_authority)
        with pytest.raises(
            supervisor_v1.V075K7AttemptProcessSupervisorV1Error,
            match="additional process launch",
        ):
            _inject_for_testing(session, test_authority)
    journal = session.close(
        supervisor_v1.AttemptProcessCloseKindV1.PROTOCOL_FAILURE
    )
    assert journal.observed_launch_count == 2
    assert journal.launch_edge_lower_bound == 2
    assert journal.close_kind is supervisor_v1.AttemptProcessCloseKindV1.PROTOCOL_FAILURE
    verification = (
        supervisor_v1.verify_v075_k7_attempt_process_raw_journal_bytes_v1(
            raw=journal.canonical_bytes,
            expected=journal,
        )
    )
    assert verification.observed_launch_count == 2
    assert verification.to_document()["formal_counter_record_authorized"] is False


def test_context_copy_cannot_emit_from_another_thread(
    test_authority,
    shared_request,
) -> None:
    session, _request_value, _execution = _bound_session(
        shared_request, test_authority
    )
    errors: list[BaseException] = []
    with session.activate_process_sink():
        def target() -> None:
            try:
                _inject_for_testing(session, test_authority)
            except BaseException as error:  # noqa: BLE001 - test capture
                errors.append(error)

        thread = Thread(target=target)
        thread.start()
        thread.join()
    assert len(errors) == 1
    assert isinstance(
        errors[0], supervisor_v1.V075K7AttemptProcessSupervisorV1Error
    )
    assert "thread" in str(errors[0])
    session.close(supervisor_v1.AttemptProcessCloseKindV1.PRELAUNCH_FAILURE)


def test_missing_launch_and_post_close_emission_are_rejected(
    test_authority,
    shared_request,
) -> None:
    session, _request_value, _execution = _bound_session(
        shared_request, test_authority
    )
    missing = session.close(supervisor_v1.AttemptProcessCloseKindV1.SUCCESS)
    assert missing.close_kind is supervisor_v1.AttemptProcessCloseKindV1.PROTOCOL_FAILURE
    assert missing.to_document()["protocol_failure_reason"] == "CLOSE_KIND_PREFIX_MISMATCH"

    postclose, _request_value, _execution = _bound_session(
        shared_request, test_authority
    )
    with postclose.activate_process_sink():
        journal = postclose.close(
            supervisor_v1.AttemptProcessCloseKindV1.PRELAUNCH_FAILURE
        )
        with pytest.raises(
            supervisor_v1.V075K7AttemptProcessSupervisorV1Error,
            match="already closed",
        ):
            _inject_for_testing(postclose, test_authority)
    assert journal.observed_launch_count == 0
    with pytest.raises(
        supervisor_v1.V075K7AttemptProcessSupervisorV1Error,
        match="already closed",
    ):
        postclose.bind_request(shared_request)


def test_request_and_raw_snapshot_mutation_fail_closed(
    test_authority,
    shared_request,
) -> None:
    session, request, _execution = _bound_session(
        shared_request, test_authority
    )
    original_nonce = request.request_nonce
    object.__setattr__(request, "request_nonce", _id("mutated-nonce"))
    mutated = session.close(
        supervisor_v1.AttemptProcessCloseKindV1.PRELAUNCH_FAILURE
    )
    assert mutated.close_kind is supervisor_v1.AttemptProcessCloseKindV1.PROTOCOL_FAILURE
    assert (
        mutated.to_document()["protocol_failure_reason"]
        == "BOUND_REQUEST_SNAPSHOT_CHANGED_BEFORE_CLOSE"
    )
    object.__setattr__(request, "request_nonce", original_nonce)

    event_session, _event_request, _event_execution = _bound_session(
        shared_request, test_authority
    )
    _inject_for_testing(event_session, test_authority)
    journal = event_session.close(
        supervisor_v1.AttemptProcessCloseKindV1.POSTLAUNCH_FAILURE
    )
    detached = journal.launch_event_documents[0]
    detached["observed_value"] = 99
    assert journal.launch_event_documents[0]["observed_value"] == 1
    supervisor_v1.verify_v075_k7_attempt_process_raw_journal_bytes_v1(
        raw=journal.canonical_bytes,
        expected=journal,
    )

    object.__setattr__(
        journal, "close_monotonic_ns", journal.close_monotonic_ns + 1
    )
    with pytest.raises(
        supervisor_v1.V075K7AttemptProcessSupervisorV1Error,
        match="changed after freeze",
    ):
        _ = journal.raw_journal_id


def test_deletion_reordering_and_cross_session_transplant_fail_closed(
    test_authority,
    shared_request,
) -> None:
    first, _request_value, _execution = _bound_session(
        shared_request, test_authority
    )
    _inject_for_testing(first, test_authority)
    with pytest.raises(
        supervisor_v1.V075K7AttemptProcessSupervisorV1Error,
        match="additional process launch",
    ):
        _inject_for_testing(first, test_authority)
    first_journal = first.close(
        supervisor_v1.AttemptProcessCloseKindV1.PROTOCOL_FAILURE
    )
    document = loads_canonical_json(first_journal.canonical_bytes)
    for attacked_document in (
        {
            **document,
            "launch_events": document["launch_events"][:-1],
            "launch_event_ids": document["launch_event_ids"][:-1],
        },
        {
            **document,
            "launch_events": list(reversed(document["launch_events"])),
            "launch_event_ids": list(
                reversed(document["launch_event_ids"])
            ),
        },
    ):
        with pytest.raises(
            supervisor_v1.V075K7AttemptProcessSupervisorV1Error,
            match="differ from the frozen snapshot",
        ):
            supervisor_v1.verify_v075_k7_attempt_process_raw_journal_bytes_v1(
                raw=canonical_json_bytes(attacked_document),
                expected=first_journal,
            )

    second, _request_value, _execution = _bound_session(
        shared_request, test_authority
    )
    _inject_for_testing(second, test_authority)
    second_journal = second.close(
        supervisor_v1.AttemptProcessCloseKindV1.POSTLAUNCH_FAILURE
    )
    with pytest.raises(
        supervisor_v1.V075K7AttemptProcessSupervisorV1Error,
        match="differ from the frozen snapshot",
    ):
        supervisor_v1.verify_v075_k7_attempt_process_raw_journal_bytes_v1(
            raw=first_journal.canonical_bytes,
            expected=second_journal,
        )


@pytest.mark.parametrize(
    "failure_site", ["provenance", "timestamp", "event_hash"]
)
def test_launch_edge_survives_event_materialization_failure(
    failure_site: str,
    monkeypatch: pytest.MonkeyPatch,
    test_authority,
    shared_request,
) -> None:
    session, _request_value, _execution = _bound_session(
        shared_request, test_authority
    )

    def injected_failure(*_args, **_kwargs):
        raise RuntimeError(f"injected {failure_site} failure")

    with monkeypatch.context() as isolated:
        if failure_site == "provenance":
            isolated.setattr(
                type(sink_v1._PINNED_RUNTIME_CALLSITE),
                "provenance",
                injected_failure,
            )
        elif failure_site == "timestamp":
            isolated.setattr(
                supervisor_v1.time, "monotonic_ns", injected_failure
            )
        else:
            original_hash = supervisor_v1._hash

            def conditional_hash(domain, payload):
                if domain == V075_K7_ATTEMPT_PROCESS_LAUNCH_EVENT_V1_DOMAIN:
                    return injected_failure()
                return original_hash(domain, payload)

            isolated.setattr(supervisor_v1, "_hash", conditional_hash)
        with pytest.raises(RuntimeError, match="injected"):
            if failure_site == "provenance":
                session._record_process_launch_from_sink_v1(
                    sink_v1._EVENT_ISSUER,
                    sink_v1._PINNED_RUNTIME_CALLSITE,
                )
            else:
                _inject_for_testing(session, test_authority)

    assert session.launch_edge_entered_count == 1
    journal = session.close(
        supervisor_v1.AttemptProcessCloseKindV1.POSTLAUNCH_FAILURE
    )
    document = journal.to_document()
    assert journal.close_kind is supervisor_v1.AttemptProcessCloseKindV1.PROTOCOL_FAILURE
    assert journal.launch_edge_lower_bound == 1
    assert journal.observed_launch_count == 0
    assert document["materialized_launch_event_count"] == 0
    assert document["raw_launch_event_list_empty"] is True
    assert document["launch_event_materialization_in_progress"] is True
    assert document["formal_vector_authorized"] is False
    verification = (
        supervisor_v1.verify_v075_k7_attempt_process_raw_journal_bytes_v1(
            raw=journal.canonical_bytes,
            expected=journal,
        )
    )
    assert verification.launch_edge_lower_bound == 1
    assert verification.observed_launch_count == 0


def test_failed_journal_close_retains_emergency_nonformal_prefix(
    monkeypatch: pytest.MonkeyPatch,
    test_authority,
    shared_request,
) -> None:
    session, _request_value, _execution = _bound_session(
        shared_request, test_authority
    )
    _inject_for_testing(session, test_authority)

    def fail_journal_materialization(*_args, **_kwargs):
        raise RuntimeError("injected raw-journal materialization failure")

    with monkeypatch.context() as isolated:
        isolated.setattr(
            supervisor_v1,
            "K7AttemptProcessRawJournalV1",
            fail_journal_materialization,
        )
        with pytest.raises(RuntimeError, match="raw-journal"):
            session.close(
                supervisor_v1.AttemptProcessCloseKindV1.POSTLAUNCH_FAILURE
            )

    emergency = loads_canonical_json(session.emergency_prefix_bytes_v1())
    assert emergency["schema"] == (
        "acfqp.v075_k7_attempt_process_emergency_prefix.v1"
    )
    assert emergency["session_state"] == "CLOSED"
    assert emergency["closure_incomplete"] is True
    assert emergency["raw_journal_issued"] is False
    assert "raw_journal_id" not in emergency
    assert emergency["launch_edge_lower_bound"] == 1
    assert emergency["materialized_launch_event_count"] == 1
    assert emergency["counter_records_issued"] is False
    assert emergency["formal_vector_authorized"] is False
    assert emergency[
        "registered_prebind_through_parent_payload_raw_prefix"
    ] is False


def test_caller_cannot_mint_launch_or_session_authority(
    monkeypatch: pytest.MonkeyPatch,
    test_authority,
) -> None:
    del test_authority
    profile = supervisor_v1.official_v075_k7_attempt_process_supervisor_profile_v1()
    with pytest.raises(
        supervisor_v1.V075K7AttemptProcessSupervisorV1Error,
        match="foreign call site",
    ):
        supervisor_v1.start_v075_k7_attempt_process_supervisor_session_v1()
    pinned_executor = supervisor_v1._PINNED_EXECUTOR_CALLSITE.function

    def monkeypatched_executor():
        return supervisor_v1.start_v075_k7_attempt_process_supervisor_session_v1()

    monkeypatch.setattr(
        executor_v1,
        "execute_v075_k7_attempt_scoped_parent_v1",
        monkeypatched_executor,
    )
    assert supervisor_v1._PINNED_EXECUTOR_CALLSITE.function is pinned_executor
    with pytest.raises(
        supervisor_v1.V075K7AttemptProcessSupervisorV1Error,
        match="foreign call site",
    ):
        monkeypatched_executor()
    with pytest.raises(
        supervisor_v1.V075K7AttemptProcessSupervisorV1Error,
        match="caller-minted",
    ):
        supervisor_v1.V075K7AttemptProcessSupervisorSessionV1(
            profile, _issuer=object()
        )
    with pytest.raises(
        supervisor_v1.V075K7AttemptProcessSupervisorV1Error,
        match="caller-minted",
    ):
        supervisor_v1.K7AttemptProcessLaunchEventV1(
            object(),
            _id("execution"),
            _id("session"),
            1,
            1,
            1,
            1,
            "TEST_ONLY_PRIVATE_AUTHORITY",
            "TEST_ONLY_EVENT_INJECTION",
            None,
            None,
            None,
            False,
            False,
            True,
        )
