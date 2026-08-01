from __future__ import annotations

from pathlib import Path

import pytest

from acfqp.phase3e_ids import canonical_json_bytes
from acfqp.phase3e_ids import V075_K7_ATTEMPT_PROCESS_RAW_JOURNAL_V1_DOMAIN
from acfqp import v075_k7_attempt_process_executor_v1 as executor
from acfqp import v075_k7_attempt_process_sink_v1 as sink
from acfqp import v075_k7_attempt_process_supervisor_v1 as supervisor
from acfqp import v075_k7_parent_atomic_executor_v1 as parent
from tests.test_v075_k7_atomic_pidfd_runtime_v1 import _id, _successor_request


def _execute(request, tmp_path: Path):
    return executor.execute_v075_k7_attempt_scoped_parent_v1(
        request=request,
        delegated_parent_fd=0,
        sealed_lifecycle_secret_fd=0,
        repository_root=tmp_path,
        signer_private_root=tmp_path,
        signer_private_key_path=tmp_path / "unused-key",
    )


def _typed_prelaunch_failure(request_id: str):
    return parent.V075K7ParentAtomicFailureV1(
        parent._FAILURE_ISSUER,  # noqa: SLF001 - exact parent fixture
        request_id,
        "NOT_APPLICABLE_SPEC_NOT_FROZEN",
        "PREPARE",
        canonical_json_bytes({"schema": "acfqp.test_parent_failure.v1"}),
        b"",
    )


def test_parent_exception_retains_zero_launch_prefix_and_no_formal_claim(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = _successor_request("attempt-wrapper-exception")

    def fail_parent(**_kwargs):
        raise RuntimeError("synthetic parent exception")

    monkeypatch.setattr(
        executor.parent_v1,
        "execute_v075_k7_parent_atomic_attempt_v1",
        fail_parent,
    )
    envelope = _execute(request, tmp_path)
    document = envelope.to_document()
    assert envelope.outcome is executor.AttemptScopedParentOutcomeV1.PARENT_EXCEPTION
    assert envelope.journal.close_kind is supervisor.AttemptProcessCloseKindV1.PRELAUNCH_FAILURE
    assert document["raw_observed_process_launches"] == 0
    assert document["process_connection_status"] == executor.CONNECTION_STATUS
    assert document["raw_count_is_not_formal_actual"] is True
    assert document["attempt_wide_raw_process_evidence"] is False
    assert document["complete_attempt_wide_raw_process_evidence"] is False
    assert (
        document["registered_prebind_through_parent_payload_raw_prefix"]
        is True
    )
    assert document["counter_records_issued"] is False
    assert document["work_vector_issued"] is False
    assert document["comparison_vector_issued"] is False


def test_typed_parent_failure_is_joined_to_exact_request(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = _successor_request("attempt-wrapper-typed")
    failure = _typed_prelaunch_failure(request.request_id)
    monkeypatch.setattr(
        executor.parent_v1,
        "execute_v075_k7_parent_atomic_attempt_v1",
        lambda **_kwargs: failure,
    )
    envelope = _execute(request, tmp_path)
    assert envelope.outcome is executor.AttemptScopedParentOutcomeV1.PARENT_TYPED_FAILURE
    assert envelope.parent_result is failure
    assert envelope.journal.observed_launch_count == 0
    assert envelope.journal.close_kind is supervisor.AttemptProcessCloseKindV1.PRELAUNCH_FAILURE

    crossed = _typed_prelaunch_failure(_id("crossed-parent-request"))
    monkeypatch.setattr(
        executor.parent_v1,
        "execute_v075_k7_parent_atomic_attempt_v1",
        lambda **_kwargs: crossed,
    )
    crossed_envelope = _execute(request, tmp_path)
    assert (
        crossed_envelope.outcome
        is executor.AttemptScopedParentOutcomeV1.PARENT_EXCEPTION
    )
    assert crossed_envelope.parent_result is None
    assert (
        crossed_envelope.parent_exception_class
        == "V075K7AttemptProcessExecutorV1Error"
    )
    assert crossed_envelope.journal.observed_launch_count == 0


def test_parent_publication_snapshot_freezes_before_process_window_close(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = _successor_request("attempt-wrapper-publication")
    failure = _typed_prelaunch_failure(request.request_id)
    original_to_document = parent.V075K7ParentAtomicFailureV1.to_document
    active_sink_observations: list[bool] = []

    def checked_to_document(self):
        active_sink_observations.append(sink._ACTIVE_SINK.get() is not None)  # noqa: SLF001
        return original_to_document(self)

    monkeypatch.setattr(
        parent.V075K7ParentAtomicFailureV1,
        "to_document",
        checked_to_document,
    )
    monkeypatch.setattr(
        executor.parent_v1,
        "execute_v075_k7_parent_atomic_attempt_v1",
        lambda **_kwargs: failure,
    )
    envelope = _execute(request, tmp_path)
    assert active_sink_observations == [True]
    envelope.to_document()
    assert active_sink_observations == [True]


def test_request_replay_occurs_inside_active_process_window(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = _successor_request("attempt-wrapper-request-window")
    failure = _typed_prelaunch_failure(request.request_id)
    request_type = type(request)
    original_assert_current = request_type._assert_current  # noqa: SLF001
    active_sink_observations: list[bool] = []

    def checked_assert_current(self):
        active_sink_observations.append(sink._ACTIVE_SINK.get() is not None)  # noqa: SLF001
        return original_assert_current(self)

    monkeypatch.setattr(request_type, "_assert_current", checked_assert_current)
    monkeypatch.setattr(
        executor.parent_v1,
        "execute_v075_k7_parent_atomic_attempt_v1",
        lambda **_kwargs: failure,
    )
    envelope = _execute(request, tmp_path)
    assert envelope.outcome is executor.AttemptScopedParentOutcomeV1.PARENT_TYPED_FAILURE
    assert active_sink_observations
    assert all(active_sink_observations)


def test_identity_bind_failure_closes_unbound_prefix(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = _successor_request("attempt-wrapper-bind")
    original_nonce = request.request_nonce
    object.__setattr__(request, "request_nonce", _id("mutated-bind-nonce"))
    called = False

    def forbidden_parent(**_kwargs):
        nonlocal called
        called = True
        raise AssertionError("parent must not run after identity bind failure")

    monkeypatch.setattr(
        executor.parent_v1,
        "execute_v075_k7_parent_atomic_attempt_v1",
        forbidden_parent,
    )
    try:
        envelope = _execute(request, tmp_path)
    finally:
        object.__setattr__(request, "request_nonce", original_nonce)
    assert called is False
    assert envelope.outcome is executor.AttemptScopedParentOutcomeV1.IDENTITY_BIND_FAILURE
    assert envelope.parent_exception_class is not None
    assert envelope.journal.execution_document is None
    assert envelope.journal.close_kind is supervisor.AttemptProcessCloseKindV1.IDENTITY_BIND_FAILURE
    assert envelope.journal.observed_launch_count == 0


def test_envelope_failure_raises_with_closed_raw_journal(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = _successor_request("attempt-wrapper-finalization")
    failure = _typed_prelaunch_failure(request.request_id)
    monkeypatch.setattr(
        executor.parent_v1,
        "execute_v075_k7_parent_atomic_attempt_v1",
        lambda **_kwargs: failure,
    )

    class BrokenEnvelope:
        def __init__(self, *_args, **_kwargs):
            raise RuntimeError("synthetic envelope failure")

    monkeypatch.setattr(
        executor,
        "V075K7AttemptScopedParentEnvelopeV1",
        BrokenEnvelope,
    )
    with pytest.raises(
        executor.V075K7AttemptProcessFinalizationV1Error
    ) as captured:
        _execute(request, tmp_path)
    assert captured.value.raw_journal_bytes is not None
    assert captured.value.emergency_prefix_bytes is None
    assert captured.value.original_exception_class == "RuntimeError"


def test_journal_close_failure_raises_with_emergency_prefix(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = _successor_request("attempt-wrapper-close-failure")
    failure = _typed_prelaunch_failure(request.request_id)
    monkeypatch.setattr(
        executor.parent_v1,
        "execute_v075_k7_parent_atomic_attempt_v1",
        lambda **_kwargs: failure,
    )

    def fail_journal(*_args, **_kwargs):
        raise RuntimeError("synthetic journal close failure")

    monkeypatch.setattr(supervisor, "K7AttemptProcessRawJournalV1", fail_journal)
    with pytest.raises(
        executor.V075K7AttemptProcessFinalizationV1Error
    ) as captured:
        _execute(request, tmp_path)
    assert captured.value.raw_journal_bytes is None
    assert captured.value.emergency_prefix_bytes is not None
    assert captured.value.emergency_prefix_snapshot is None
    assert captured.value.original_exception_class == "RuntimeError"


def test_shared_hash_and_emergency_encoding_failure_retains_raw_snapshot(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = _successor_request("attempt-wrapper-dual-prefix-failure")
    failure = _typed_prelaunch_failure(request.request_id)
    monkeypatch.setattr(
        executor.parent_v1,
        "execute_v075_k7_parent_atomic_attempt_v1",
        lambda **_kwargs: failure,
    )
    original_hash = supervisor._hash  # noqa: SLF001
    original_canonical = supervisor.canonical_json_bytes

    def attacked_hash(domain, payload):
        if domain == V075_K7_ATTEMPT_PROCESS_RAW_JOURNAL_V1_DOMAIN:
            raise RuntimeError("synthetic raw-journal hash failure")
        return original_hash(domain, payload)

    def attacked_canonical(value):
        if (
            type(value) is dict
            and value.get("schema")
            == "acfqp.v075_k7_attempt_process_emergency_prefix.v1"
        ):
            raise RuntimeError("synthetic emergency encoding failure")
        return original_canonical(value)

    monkeypatch.setattr(supervisor, "_hash", attacked_hash)
    monkeypatch.setattr(supervisor, "canonical_json_bytes", attacked_canonical)
    with pytest.raises(
        executor.V075K7AttemptProcessFinalizationV1Error
    ) as captured:
        _execute(request, tmp_path)
    assert captured.value.raw_journal_bytes is None
    assert captured.value.emergency_prefix_bytes is None
    snapshot = captured.value.emergency_prefix_snapshot
    assert snapshot is not None
    assert snapshot[0] == (
        "acfqp.v075_k7_attempt_process_emergency_prefix_snapshot.v1"
    )
    assert snapshot[7] == 0
