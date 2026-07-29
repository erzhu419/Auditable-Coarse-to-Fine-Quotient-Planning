from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
import hashlib
import importlib.util
from pathlib import Path
import subprocess
import sys

import pytest

from acfqp import v075_batched_observer_authority_v1 as batch
from acfqp import v075_batched_observer_ipc_v1 as ipc
from acfqp import v075_private_observer_boundary_v1 as observer
from tests.test_v075_private_observer_boundary_v1 import (
    _ConstructionSigner,
    _fixture,
    _id,
    _namespace,
    _salt,
    _streams,
    _synthetic_environment,
)


def _setup(
    marker: str,
    *,
    behavior: ipc.V075IPCConstructionBehaviorV1 = (
        ipc.V075IPCConstructionBehaviorV1.HONEST
    ),
    script_counts: tuple[int, ...] = (7, 11, 13),
):
    namespace = _namespace("ipc-" + marker)
    authority = _fixture(namespace, "ipc-" + marker)
    session = observer.open_construction_private_observer_fixture_v1(
        authority=authority,
        private_salt=_salt("ipc-" + marker),
        private_environment=_synthetic_environment(),
        observer_signer=_ConstructionSigner(),
        session_external_id=_id("ipc-session-" + marker),
    )
    wrapped = batch.wrap_v075_construction_batched_observer_session_v1(
        session
    )
    stream = _streams(namespace).streams[0]
    profile = ipc.freeze_v075_construction_ipc_occurrence_profile_v1(
        occurrence_id=_id("ipc-occurrence-" + marker),
        streams=(stream,),
        script=tuple((stream.stream_id, count) for count in script_counts),
        accepted_draw_cap_by_stream={stream.stream_id: 128},
        behavior=behavior,
        max_batches=8,
        max_total_accepted_draws=128,
        process_timeout_seconds=60,
    )
    replay_environment = (
        batch.issue_v075_construction_batch_replay_environment_fixture_v1(
            namespace=namespace,
            private_salt=_salt("ipc-" + marker),
            private_environment=_synthetic_environment(),
        )
    )
    return profile, wrapped, authority, replay_environment


def _run(values):
    profile, wrapped, authority, replay_environment = values
    return ipc.execute_v075_construction_ipc_occurrence_v1(
        profile=profile,
        batched_session=wrapped,
        private_replay_authority=authority,
        private_replay_environment=replay_environment,
    )


def test_one_fresh_process_observes_only_after_typed_intents() -> None:
    profile, wrapped, authority, replay_environment = _setup(
        "honest",
        script_counts=(7, 11),
    )
    result = _run((profile, wrapped, authority, replay_environment))
    assert result.status == "PASS"
    assert result.terminal_code == "CONSTRUCTION_FIXTURE_PASS"
    assert result.actual_work.process_launches == 1
    assert result.actual_work.child_intents_received == 2
    assert result.actual_work.parent_batches_issued == 2
    assert result.actual_work.observer_accepted_draws == 18
    assert result.actual_work.private_replay_batches == 2
    assert result.scientific_payload["accepted_draw_count"] == 18
    assert result.scientific_payload["completed_batch_count"] == 2
    assert [entry.direction for entry in result.journal_entries] == [
        "CHILD_TO_PARENT",
        "PARENT_TO_CHILD",
        "CHILD_TO_PARENT",
        "PARENT_TO_CHILD",
        "CHILD_TO_PARENT",
    ]
    assert result.journal_entries[-1].message_id == (
        result.scientific_payload_id
    )
    closure = result.batch_occurrence_closure
    assert closure.batch_ids == tuple(
        item.batch_id for item in wrapped.batches
    )
    assert closure.accepted_draw_count == 18
    assert closure.stream_ids == (profile.row_catalogue[0].stream_id,)
    assert len(closure.sequence_verification_ids) == 1
    assert len(closure.private_replay_verification_ids) == 2
    assert closure.to_document()["every_batch_private_replayed"] is True
    assert getattr(wrapped._session, "_closed") is True
    independent = ipc.verify_v075_signed_batch_occurrence_closure_v1(
        closure=closure,
        profile=profile,
        journal_entries=result.journal_entries,
        batches=result.observed_batches,
        private_replays=result.private_replay_verifications,
    )
    assert independent.verification_id == (
        result.batch_occurrence_closure_verification.verification_id
    )
    with pytest.raises(ipc.V075BatchedObserverIPCInvariantViolation):
        replace(closure, occurrence_id=_id("closure-transplant"))


def test_child_entrypoint_is_stdlib_only_and_has_no_private_modules() -> None:
    path = Path(ipc.__file__).resolve()
    command = [
        sys.executable,
        "-I",
        "-c",
        (
            "import runpy,sys;"
            f"sys.argv=[{str(path)!r},'--not-child'];"
            f"runpy.run_path({str(path)!r},run_name='not_main');"
            "print('|'.join(sorted(k for k in sys.modules "
            "if k.startswith('acfqp') or k.startswith('tests'))))"
        ),
    ]
    completed = subprocess.run(
        command,
        check=True,
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert completed.stdout.strip() == ""
    source = path.read_text(encoding="utf-8")
    assert "pickle." not in source
    assert "callback(" not in source


def test_sequential_and_parallel_scientific_payloads_are_byte_identical() -> None:
    markers = ("schedule-a", "schedule-b")

    sequential = []
    for marker in markers:
        sequential.append(_run(_setup(marker, script_counts=(5,))))

    def run(marker: str):
        return _run(_setup(marker, script_counts=(5,)))

    with ThreadPoolExecutor(max_workers=2) as pool:
        parallel = tuple(pool.map(run, reversed(markers)))
    by_id = {result.occurrence_id: result for result in parallel}
    assert all(result.status == "PASS" for result in sequential)
    for expected in sequential:
        actual = by_id[expected.occurrence_id]
        assert (
            actual.canonical_scientific_bytes
            == expected.canonical_scientific_bytes
        )
        assert actual.scientific_payload_id == expected.scientific_payload_id
        # Diagnostics remain a separate lane and are never in scientific bytes.
        assert "stderr_sha256" not in actual.scientific_payload
        assert "process_exit_code" not in actual.scientific_payload


@pytest.mark.parametrize(
    ("behavior", "expected_batches", "terminal"),
    (
        (
            ipc.V075IPCConstructionBehaviorV1.GAP_FIRST_INTENT,
            0,
            "PROTOCOL_FAILURE",
        ),
        (
            ipc.V075IPCConstructionBehaviorV1.REPLAY_FIRST_INTENT,
            1,
            "PROTOCOL_FAILURE",
        ),
        (
            ipc.V075IPCConstructionBehaviorV1.TRANSPLANT_FIRST_INTENT,
            0,
            "PROTOCOL_FAILURE",
        ),
        (
            ipc.V075IPCConstructionBehaviorV1.TAMPER_FINAL_PAYLOAD,
            1,
            "PROTOCOL_FAILURE",
        ),
        (
            ipc.V075IPCConstructionBehaviorV1.CRASH_BEFORE_INTENT,
            0,
            "PROCESS_FAILURE",
        ),
    ),
)
def test_gap_replay_transplant_tamper_and_process_failure_close_fail_closed(
    behavior: ipc.V075IPCConstructionBehaviorV1,
    expected_batches: int,
    terminal: str,
) -> None:
    script_counts = (
        (3, 5)
        if behavior
        is ipc.V075IPCConstructionBehaviorV1.REPLAY_FIRST_INTENT
        else (3,)
    )
    profile, wrapped, authority, replay_environment = _setup(
        "attack-" + behavior.value,
        behavior=behavior,
        script_counts=script_counts,
    )
    result = _run((profile, wrapped, authority, replay_environment))
    assert result.status == "FAILED"
    assert result.terminal_code == terminal
    assert result.scientific_payload is None
    assert result.actual_work.parent_batches_issued == expected_batches
    assert result.actual_work.process_launches == 1
    assert result.actual_work.observer_accepted_draws == sum(
        entry.request.accepted_draw_count for entry in wrapped.batches
    )


def test_profile_rejects_cross_context_arm_row_and_cap_transplants() -> None:
    profile, _wrapped, _authority, _replay = _setup("profile-attacks")
    entry = profile.row_catalogue[0]
    with pytest.raises(ipc.V075BatchedObserverIPCInvariantViolation):
        replace(profile, context_id=_id("different-context"))
    with pytest.raises(ipc.V075BatchedObserverIPCInvariantViolation):
        replace(profile, arm="NO_PRIOR")
    with pytest.raises(ipc.V075BatchedObserverIPCInvariantViolation):
        replace(entry, accepted_draw_cap=0)
    with pytest.raises(ipc.V075BatchedObserverIPCInvariantViolation):
        ipc.freeze_v075_construction_ipc_occurrence_profile_v1(
            occurrence_id=_id("bad-script"),
            streams=(entry.stream_identity,),
            script=((_id("foreign-stream"), 1),),
            accepted_draw_cap_by_stream={entry.stream_id: 10},
        )


def test_profile_and_launch_contain_no_private_runtime_objects() -> None:
    profile, _wrapped, _authority, _replay = _setup("public-only")
    document = profile.to_document()
    raw = ipc._canonical_bytes(document)
    lowered = raw.lower()
    assert b"secret_laws" not in lowered
    assert b"private_salt" not in lowered
    assert b"private_exponent" not in lowered
    assert b"callback_serialized\":true" not in lowered
    assert b"pickle_transport_allowed\":true" not in lowered
    assert profile.program_registration.argv == ("--acfqp-v075-child",)
    assert profile.program_registration.arbitrary_callback_allowed is False
    assert profile.program_registration.pickle_transport_allowed is False


def test_production_readiness_remains_explicitly_locked() -> None:
    assert ipc.CONSTRUCTION_FIXTURE_ONLY is True
    assert ipc.PRODUCTION_EXECUTION_STATUS.startswith("NOT_READY_")
    assert "PRODUCTION" not in {
        member.name for member in ipc.V075IPCChildProgramV1
    }
