from __future__ import annotations

import multiprocessing
import hashlib
import os
import pickle
from pathlib import Path
import shutil
import tempfile
import threading

import pytest

from acfqp import construction_k7_h1_attempt_rejection_gate_v1 as gate_v1
from acfqp.phase3e_ids import canonical_json_bytes


@pytest.fixture
def tmp_path() -> Path:
    path = Path(tempfile.mkdtemp(prefix="acfqp-h1-rejection-", dir="/tmp"))
    try:
        yield path
    finally:
        shutil.rmtree(path)


def _id(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _spec(
    base_directory: Path,
    suffix: str = "base",
) -> gate_v1.H1AttemptRejectionGateSpecV1:
    return gate_v1.freeze_h1_attempt_rejection_gate_spec_v1(
        base_directory=base_directory,
        logical_occurrence_id=_id(f"occurrence-{suffix}"),
        route_attempt_id=_id(f"attempt-{suffix}"),
        caller_pinned_lifecycle_provenance_id=_id(f"provenance-{suffix}"),
    )


def _gate(tmp_path: Path, suffix: str = "base") -> gate_v1.H1AttemptRejectionGateHandleV1:
    return gate_v1.initialize_h1_attempt_rejection_gate_v1(
        tmp_path,
        _spec(tmp_path, suffix),
    )


def _commit(
    gate: gate_v1.H1AttemptRejectionGateHandleV1,
    *,
    source: gate_v1.H1RejectionSourceKindV1 = gate_v1.H1RejectionSourceKindV1.SHARED_OWNER,
    candidate: int = 11,
    decision_point_id: str | None = None,
    transaction_id: str | None = None,
    shared_owner_profile_core_id: str | None = None,
    rejection_request_id: str | None = None,
    crash: gate_v1.H1AttemptRejectionCrashPointV1 = gate_v1.H1AttemptRejectionCrashPointV1.NONE,
) -> gate_v1.H1AttemptRejectionCommitV1:
    return gate_v1.commit_h1_attempt_rejection_v1(
        gate,
        writer_role=gate_v1.H1AttemptRejectionWriterRoleV1.BROKER,
        decision_point_id=decision_point_id or _id("decision-base"),
        transaction_id=transaction_id or _id("transaction-base"),
        shared_owner_profile_core_id=(
            shared_owner_profile_core_id or _id("owner-core-base")
        ),
        rejection_request_id=(rejection_request_id or _id(f"request-{candidate}")),
        source_kind=source,
        site_key="read:sealed-input:0",
        path="io.read_bytes",
        limit_kind=gate_v1.H1RejectionLimitKindV1.SHARED_PATH,
        reservation_upper=4,
        candidate=candidate,
        hard_cap=10,
        reason_code="SHARED_CAP_EXHAUSTED",
        crash_point=crash,
    )


def _concurrent_commit_worker(
    gate_directory: str,
    gate_id: str,
    candidate: int,
    queue: multiprocessing.Queue,
) -> None:
    try:
        handle = gate_v1.open_h1_attempt_rejection_gate_v1(
            gate_directory,
            expected_gate_id=gate_id,
        )
        value = _commit(handle, candidate=candidate)
        queue.put(("OK", value.commit_id))
    except BaseException as error:
        queue.put((type(error).__name__, str(error)))


def _guard_worker(
    gate_directory: str,
    gate_id: str,
    entered: multiprocessing.Event,
    release: multiprocessing.Event,
    queue: multiprocessing.Queue,
) -> None:
    try:
        handle = gate_v1.open_h1_attempt_rejection_gate_v1(
            gate_directory,
            expected_gate_id=gate_id,
        )
        with gate_v1.hold_h1_attempt_gate_open_for_side_effect_v1(handle):
            entered.set()
            if not release.wait(timeout=10):
                raise RuntimeError("test guard release timed out")
        queue.put(("GUARD_RELEASED", ""))
    except BaseException as error:
        queue.put((type(error).__name__, str(error)))


def _ready_commit_worker(
    gate_directory: str,
    gate_id: str,
    ready: multiprocessing.Event,
    queue: multiprocessing.Queue,
) -> None:
    try:
        ready.set()
        handle = gate_v1.open_h1_attempt_rejection_gate_v1(
            gate_directory,
            expected_gate_id=gate_id,
        )
        value = _commit(handle)
        queue.put(("COMMITTED", value.commit_id))
    except BaseException as error:
        queue.put((type(error).__name__, str(error)))


def _delayed_ready_commit_worker(
    gate_directory: str,
    gate_id: str,
    ready: multiprocessing.Event,
    start: multiprocessing.Event,
    queue: multiprocessing.Queue,
) -> None:
    try:
        ready.set()
        if not start.wait(timeout=10):
            raise RuntimeError("test commit start timed out")
        handle = gate_v1.open_h1_attempt_rejection_gate_v1(
            gate_directory,
            expected_gate_id=gate_id,
        )
        value = _commit(handle)
        queue.put(("COMMITTED", value.commit_id))
    except BaseException as error:
        queue.put((type(error).__name__, str(error)))


def _enter_context(manager: object) -> None:
    with manager:  # type: ignore[attr-defined]
        pass


def _paused_cursor_append_commit_worker(
    gate_directory: str,
    gate_id: str,
    cursor_partial: multiprocessing.Event,
    release: multiprocessing.Event,
    queue: multiprocessing.Queue,
) -> None:
    """Expose a deterministic partial cursor append while retaining gate EX."""

    try:
        handle = gate_v1.open_h1_attempt_rejection_gate_v1(
            gate_directory,
            expected_gate_id=gate_id,
        )
        cursor_metadata = (Path(gate_directory) / "high-water.cursor").stat()
        cursor_identity = (cursor_metadata.st_dev, cursor_metadata.st_ino)
        original_write_all = gate_v1._write_all
        paused = False

        def pause_cursor_write(descriptor: int, raw: bytes) -> None:
            nonlocal paused
            metadata = os.fstat(descriptor)
            if not paused and (metadata.st_dev, metadata.st_ino) == cursor_identity:
                paused = True
                split = max(1, len(raw) // 2)
                original_write_all(descriptor, raw[:split])
                os.fsync(descriptor)
                cursor_partial.set()
                if not release.wait(timeout=10):
                    raise RuntimeError("test cursor append release timed out")
                original_write_all(descriptor, raw[split:])
                return
            original_write_all(descriptor, raw)

        gate_v1._write_all = pause_cursor_write
        value = _commit(handle)
        queue.put(("COMMITTED", value.commit_id))
    except BaseException as error:
        queue.put((type(error).__name__, str(error)))


def _validation_during_cursor_append_worker(
    mode: str,
    gate: gate_v1.H1AttemptRejectionGateHandleV1,
    base_directory: str,
    queue: multiprocessing.Queue,
) -> None:
    try:
        if mode == "open":
            gate_v1.open_h1_attempt_rejection_gate_v1(
                gate.gate_directory,
                expected_gate_id=gate.spec.gate_id,
            )
        elif mode == "initialize":
            gate_v1.initialize_h1_attempt_rejection_gate_v1(
                base_directory,
                gate.spec,
            )
        elif mode == "require-handle":
            gate_v1.h1_attempt_rejection_gate_snapshot_v1(gate)
        else:  # pragma: no cover - test helper invariant
            raise AssertionError(f"unknown validation mode {mode}")
        queue.put(("VALIDATED", mode))
    except BaseException as error:
        queue.put((type(error).__name__, str(error)))


def test_gate_spec_is_durable_but_non_authorizing(tmp_path: Path) -> None:
    gate = _gate(tmp_path)
    reopened = gate_v1.open_h1_attempt_rejection_gate_v1(
        gate.gate_directory,
        expected_gate_id=gate.spec.gate_id,
    )
    assert reopened.spec.to_document() == gate.spec.to_document()
    document = reopened.spec.to_document()
    assert document["attempt_wide"] is True
    assert document["max_cap_rejections"] == 1
    gate_base = tmp_path / ".acfqp-h1-attempt-rejection-v1"
    assert document["gate_base_realpath"] == str(gate_base.resolve())
    assert document["gate_base_device"] == gate_base.stat().st_dev
    assert document["gate_base_inode"] == gate_base.stat().st_ino
    assert document["production_activation_chain_verified"] is False
    assert document["kernel_writer_credential_verified"] is False
    assert document["formal_counter_eligible"] is False
    assert gate_v1.recover_h1_attempt_rejection_gate_v1(gate).value == "OPEN"
    snapshot = gate_v1.h1_attempt_rejection_gate_snapshot_v1(gate)
    assert snapshot["control_cap_rejections"] == 0
    assert snapshot["native_zero_eligible"] is False

    cursor = Path(gate.gate_directory) / "high-water.cursor"
    allocation = (
        gate_base
        / f".acfqp-h1-attempt-slot-commit-{gate.spec.route_attempt_id}.json"
    )
    allocation_document = gate_v1.loads_canonical_json(allocation.read_bytes())
    cursor_genesis = gate_v1.loads_canonical_json(cursor.read_bytes().rstrip(b"\n"))
    assert allocation_document["high_water_cursor_device"] == cursor.stat().st_dev
    assert allocation_document["high_water_cursor_inode"] == cursor.stat().st_ino
    assert allocation_document["high_water_cursor_token"] == cursor_genesis[
        "cursor_token"
    ]
    assert allocation_document["high_water_cursor_genesis_record_id"] == (
        cursor_genesis["cursor_record_id"]
    )


def test_commit_is_one_inode_idempotent_and_acknowledged(tmp_path: Path) -> None:
    gate = _gate(tmp_path)
    first = _commit(gate)
    second = _commit(gate)
    assert first.to_document() == second.to_document()
    directory = Path(gate.gate_directory)
    assert (directory / "intent.json").stat().st_ino == (
        directory / "commit.json"
    ).stat().st_ino
    assert gate_v1.recover_h1_attempt_rejection_gate_v1(gate).value == (
        "COMMITTED_UNACKNOWLEDGED"
    )
    ack = gate_v1.acknowledge_h1_attempt_rejection_v1(
        gate,
        first,
        writer_role=gate_v1.H1AttemptRejectionWriterRoleV1.BROKER,
        shared_owner_receipt_id=_id("receipt"),
        shared_owner_event_id=_id("event"),
        shared_owner_snapshot_id=_id("snapshot"),
    )
    replay = gate_v1.acknowledge_h1_attempt_rejection_v1(
        gate,
        second,
        writer_role=gate_v1.H1AttemptRejectionWriterRoleV1.BROKER,
        shared_owner_receipt_id=_id("receipt"),
        shared_owner_event_id=_id("event"),
        shared_owner_snapshot_id=_id("snapshot"),
    )
    assert ack.to_document() == replay.to_document()
    assert gate_v1.recover_h1_attempt_rejection_gate_v1(gate).value == "ACKNOWLEDGED"
    snapshot = gate_v1.h1_attempt_rejection_gate_snapshot_v1(gate)
    assert snapshot["control_cap_rejections"] == 1
    assert snapshot["formal_counter_eligible"] is False


def test_shared_and_business_rejections_share_one_attempt_slot(tmp_path: Path) -> None:
    gate = _gate(tmp_path)
    _commit(gate, source=gate_v1.H1RejectionSourceKindV1.SHARED_OWNER)
    with pytest.raises(gate_v1.H1AttemptSecondRejectionV1, match="already owns"):
        _commit(
            gate,
            source=gate_v1.H1RejectionSourceKindV1.BUSINESS_ENGINE,
            candidate=12,
        )
    assert gate_v1.h1_attempt_rejection_gate_snapshot_v1(gate)[
        "control_cap_rejections"
    ] == 1


def test_attempt_slot_cannot_be_reissued_for_another_transaction_or_profile(
    tmp_path: Path,
) -> None:
    gate = _gate(tmp_path, "attempt-scope")
    _commit(gate)
    with pytest.raises(gate_v1.H1AttemptSecondRejectionV1):
        _commit(gate, rejection_request_id=_id("different-identical-request"))
    with pytest.raises(gate_v1.H1AttemptSecondRejectionV1):
        _commit(
            gate,
            candidate=12,
            decision_point_id=_id("decision-transaction-2"),
            transaction_id=_id("transaction-2"),
            shared_owner_profile_core_id=_id("owner-core-transaction-2"),
        )
    with pytest.raises(ValueError, match="allocation intent conflicts"):
        gate_v1.freeze_h1_attempt_rejection_gate_spec_v1(
            base_directory=tmp_path,
            logical_occurrence_id=gate.spec.logical_occurrence_id,
            route_attempt_id=gate.spec.route_attempt_id,
            caller_pinned_lifecycle_provenance_id=_id("changed-provenance"),
        )


def test_crash_after_intent_recovers_same_commit_without_reexecution(
    tmp_path: Path,
) -> None:
    gate = _gate(tmp_path)
    with pytest.raises(gate_v1.H1AttemptRejectionInjectedCrashV1):
        _commit(
            gate,
            crash=gate_v1.H1AttemptRejectionCrashPointV1.AFTER_INTENT_FSYNC,
        )
    directory = Path(gate.gate_directory)
    assert (directory / "intent.json").is_file()
    assert not (directory / "commit.json").exists()
    assert gate_v1.recover_h1_attempt_rejection_gate_v1(gate).value == (
        "COMMITTED_UNACKNOWLEDGED"
    )
    recovered = gate_v1.read_h1_attempt_rejection_commit_v1(gate)
    assert recovered is not None
    assert _commit(gate).commit_id == recovered.commit_id


def test_invalid_ack_operands_do_not_recover_or_mutate_intent_prefix(
    tmp_path: Path,
) -> None:
    gate = _gate(tmp_path, "ack-preflight")
    with pytest.raises(gate_v1.H1AttemptRejectionInjectedCrashV1):
        _commit(
            gate,
            crash=gate_v1.H1AttemptRejectionCrashPointV1.AFTER_INTENT_FSYNC,
        )
    directory = Path(gate.gate_directory)
    commit = gate_v1._commit_from_document(
        gate_v1.loads_canonical_json((directory / "intent.json").read_bytes())
    )
    cursor_before = (directory / "high-water.cursor").read_bytes()
    assert not (directory / "commit.json").exists()

    with pytest.raises(ValueError, match="content ID"):
        gate_v1.acknowledge_h1_attempt_rejection_v1(
            gate,
            commit,
            writer_role=gate_v1.H1AttemptRejectionWriterRoleV1.BROKER,
            shared_owner_receipt_id="not-a-content-id",
            shared_owner_event_id=_id("ack-preflight-event"),
            shared_owner_snapshot_id=_id("ack-preflight-snapshot"),
        )

    assert not (directory / "commit.json").exists()
    assert (directory / "high-water.cursor").read_bytes() == cursor_before


def test_crash_after_commit_or_ack_replays_deterministically(tmp_path: Path) -> None:
    gate = _gate(tmp_path)
    with pytest.raises(gate_v1.H1AttemptRejectionInjectedCrashV1):
        _commit(
            gate,
            crash=gate_v1.H1AttemptRejectionCrashPointV1.AFTER_COMMIT_FSYNC,
        )
    commit = gate_v1.read_h1_attempt_rejection_commit_v1(gate)
    assert commit is not None
    with pytest.raises(gate_v1.H1AttemptRejectionInjectedCrashV1):
        gate_v1.acknowledge_h1_attempt_rejection_v1(
            gate,
            commit,
            writer_role=gate_v1.H1AttemptRejectionWriterRoleV1.BROKER,
            shared_owner_receipt_id=_id("receipt-crash"),
            shared_owner_event_id=_id("event-crash"),
            shared_owner_snapshot_id=_id("snapshot-crash"),
            crash_point=gate_v1.H1AttemptRejectionCrashPointV1.AFTER_ACK_FSYNC,
        )
    assert gate_v1.recover_h1_attempt_rejection_gate_v1(gate).value == "ACKNOWLEDGED"


@pytest.mark.parametrize("same_request", [True, False])
def test_two_process_rejection_race_has_one_durable_commit(
    tmp_path: Path,
    same_request: bool,
) -> None:
    gate = _gate(tmp_path, suffix=f"race-{same_request}")
    context = multiprocessing.get_context("fork")
    queue = context.Queue()
    candidates = (11, 11 if same_request else 12)
    processes = [
        context.Process(
            target=_concurrent_commit_worker,
            args=(gate.gate_directory, gate.spec.gate_id, candidate, queue),
        )
        for candidate in candidates
    ]
    for process in processes:
        process.start()
    for process in processes:
        process.join(timeout=20)
        assert process.exitcode == 0
    results = [queue.get(timeout=5), queue.get(timeout=5)]
    oks = [row for row in results if row[0] == "OK"]
    if same_request:
        assert len(oks) == 2
        assert oks[0][1] == oks[1][1]
    else:
        assert len(oks) == 1
        assert any(row[0] == "H1AttemptSecondRejectionV1" for row in results)
    assert gate_v1.h1_attempt_rejection_gate_snapshot_v1(gate)[
        "control_cap_rejections"
    ] == 1


@pytest.mark.parametrize("mode", ["open", "initialize", "require-handle"])
def test_validation_waits_for_complete_cursor_append_before_replay(
    tmp_path: Path,
    mode: str,
) -> None:
    gate = _gate(tmp_path, suffix=f"cursor-lock-{mode}")
    context = multiprocessing.get_context("fork")
    cursor_partial = context.Event()
    release = context.Event()
    writer_queue = context.Queue()
    validation_queue = context.Queue()
    writer = context.Process(
        target=_paused_cursor_append_commit_worker,
        args=(
            gate.gate_directory,
            gate.spec.gate_id,
            cursor_partial,
            release,
            writer_queue,
        ),
    )
    writer.start()
    assert cursor_partial.wait(timeout=10)

    validator = context.Process(
        target=_validation_during_cursor_append_worker,
        args=(mode, gate, str(tmp_path), validation_queue),
    )
    validator.start()
    validator.join(timeout=0.25)
    assert validator.is_alive(), "validation read the torn cursor before locking"

    release.set()
    writer.join(timeout=10)
    validator.join(timeout=10)
    assert writer.exitcode == 0
    assert validator.exitcode == 0
    assert writer_queue.get(timeout=5)[0] == "COMMITTED"
    assert validation_queue.get(timeout=5) == ("VALIDATED", mode)
    assert gate_v1.h1_attempt_rejection_gate_snapshot_v1(gate)["state"] == (
        "COMMITTED_UNACKNOWLEDGED"
    )


def test_oversized_commit_is_rejected_before_any_gate_mutation(
    tmp_path: Path,
) -> None:
    gate = _gate(tmp_path, "oversized-commit")
    directory = Path(gate.gate_directory)
    cursor_before = (directory / "high-water.cursor").read_bytes()
    with pytest.raises(ValueError, match="byte cap before publication"):
        gate_v1.commit_h1_attempt_rejection_v1(
            gate,
            writer_role=gate_v1.H1AttemptRejectionWriterRoleV1.BROKER,
            decision_point_id=_id("oversized-decision"),
            transaction_id=_id("oversized-transaction"),
            shared_owner_profile_core_id=_id("oversized-owner-core"),
            rejection_request_id=_id("oversized-request"),
            source_kind=gate_v1.H1RejectionSourceKindV1.SHARED_OWNER,
            site_key="x" * (gate_v1._MAX_DOCUMENT_BYTES + 1),
            path="io.read_bytes",
            limit_kind=gate_v1.H1RejectionLimitKindV1.SHARED_PATH,
            reservation_upper=4,
            candidate=11,
            hard_cap=10,
            reason_code="SHARED_CAP_EXHAUSTED",
        )
    assert not (directory / "intent.json").exists()
    assert not (directory / "commit.json").exists()
    assert not (directory / "ack.json").exists()
    assert (directory / "high-water.cursor").read_bytes() == cursor_before
    assert gate_v1.h1_attempt_rejection_gate_snapshot_v1(gate)["state"] == "OPEN"


def test_rejection_blocks_later_side_effect_and_nonbroker_writes(tmp_path: Path) -> None:
    gate = _gate(tmp_path)
    with pytest.raises(ValueError, match="TOCTOU-unsafe"):
        gate_v1.require_h1_attempt_gate_open_before_side_effect_v1(gate)
    with gate_v1.hold_h1_attempt_gate_open_for_side_effect_v1(gate):
        pass
    with pytest.raises(ValueError, match="only the broker"):
        gate_v1.commit_h1_attempt_rejection_v1(
            gate,
            writer_role=gate_v1.H1AttemptRejectionWriterRoleV1.WORKER,
            decision_point_id=_id("decision-base"),
            transaction_id=_id("transaction-base"),
            shared_owner_profile_core_id=_id("owner-core-base"),
            rejection_request_id=_id("request-nonbroker"),
            source_kind=gate_v1.H1RejectionSourceKindV1.SHARED_OWNER,
            site_key="read:sealed-input:0",
            path="io.read_bytes",
            limit_kind=gate_v1.H1RejectionLimitKindV1.SHARED_PATH,
            reservation_upper=4,
            candidate=11,
            hard_cap=10,
            reason_code="SHARED_CAP_EXHAUSTED",
        )
    _commit(gate)
    with pytest.raises(gate_v1.H1AttemptRejectedV1, match="side effects are forbidden"):
        with gate_v1.hold_h1_attempt_gate_open_for_side_effect_v1(gate):
            pass


@pytest.mark.parametrize(
    "active_mode",
    ["admission", "side-effect", "dependent-replay"],
)
def test_same_thread_same_gate_reentry_matrix_fails_before_io(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    active_mode: str,
) -> None:
    gate = _gate(tmp_path, f"reentry-{active_mode}")
    other_gate = _gate(tmp_path, f"reentry-other-{active_mode}")
    fabricated_commit = gate_v1._build_commit(
        gate.spec,
        decision_point_id=_id(f"reentry-decision-{active_mode}"),
        transaction_id=_id(f"reentry-transaction-{active_mode}"),
        shared_owner_profile_core_id=_id(f"reentry-owner-{active_mode}"),
        rejection_request_id=_id(f"reentry-request-{active_mode}"),
        source_kind=gate_v1.H1RejectionSourceKindV1.SHARED_OWNER,
        site_key="read:sealed-input:0",
        path="io.read_bytes",
        limit_kind=gate_v1.H1RejectionLimitKindV1.SHARED_PATH,
        reservation_upper=4,
        candidate=11,
        hard_cap=10,
        reason_code="SHARED_CAP_EXHAUSTED",
    )
    if active_mode == "admission":
        manager = gate_v1.hold_h1_attempt_gate_open_for_admission_v1(gate)
    elif active_mode == "side-effect":
        manager = gate_v1.hold_h1_attempt_gate_open_for_side_effect_v1(gate)
    else:
        manager = gate_v1.hold_h1_attempt_rejection_gate_for_replay_v1(gate)

    with manager as active_value:
        # Contexts are keyed by gate ID, not process-global: another gate works.
        assert gate_v1.h1_attempt_rejection_gate_snapshot_v1(other_gate)[
            "state"
        ] == "OPEN"

        ordinary_calls = {
            "open": lambda: gate_v1.open_h1_attempt_rejection_gate_v1(
                gate.gate_directory,
                expected_gate_id=gate.spec.gate_id,
            ),
            "initialize": lambda: gate_v1.initialize_h1_attempt_rejection_gate_v1(
                tmp_path,
                gate.spec,
            ),
            "direct-commit": lambda: _commit(gate),
            "recover": lambda: gate_v1.recover_h1_attempt_rejection_gate_v1(gate),
            "snapshot": lambda: gate_v1.h1_attempt_rejection_gate_snapshot_v1(gate),
            "read": lambda: gate_v1.read_h1_attempt_rejection_commit_v1(gate),
            "ack": lambda: gate_v1.acknowledge_h1_attempt_rejection_v1(
                gate,
                fabricated_commit,
                writer_role=gate_v1.H1AttemptRejectionWriterRoleV1.BROKER,
                shared_owner_receipt_id=_id("reentry-receipt"),
                shared_owner_event_id=_id("reentry-event"),
                shared_owner_snapshot_id=_id("reentry-snapshot"),
            ),
            "point-check": lambda: (
                gate_v1.require_h1_attempt_gate_open_before_side_effect_v1(gate)
            ),
            "nested-admission": lambda: _enter_context(
                gate_v1.hold_h1_attempt_gate_open_for_admission_v1(gate)
            ),
            "nested-side-effect": lambda: _enter_context(
                gate_v1.hold_h1_attempt_gate_open_for_side_effect_v1(gate)
            ),
            "nested-replay": lambda: _enter_context(
                gate_v1.hold_h1_attempt_rejection_gate_for_replay_v1(gate)
            ),
        }

        def forbidden_io(*args: object, **kwargs: object) -> None:
            raise AssertionError("same-gate reentry reached filesystem I/O")

        with monkeypatch.context() as locked_io:
            locked_io.setattr(gate_v1, "_open_directory_fd", forbidden_io)
            locked_io.setattr(gate_v1, "_open_parent_directory_fd", forbidden_io)
            locked_io.setattr(gate_v1, "_open_directory_fd_at", forbidden_io)
            for _api_name, invoke in ordinary_calls.items():
                with pytest.raises(
                    ValueError,
                    match="cannot re-enter active same-gate context",
                ) as captured:
                    invoke()
                assert "only the active admission lease commit" in str(
                    captured.value
                )

        if active_mode == "admission":
            assert isinstance(
                active_value,
                gate_v1.H1AttemptRejectionAdmissionLeaseV1,
            )
            committed = gate_v1.commit_h1_attempt_rejection_with_admission_lease_v1(
                active_value,
                writer_role=gate_v1.H1AttemptRejectionWriterRoleV1.BROKER,
                decision_point_id=fabricated_commit.decision_point_id,
                transaction_id=fabricated_commit.transaction_id,
                shared_owner_profile_core_id=(
                    fabricated_commit.shared_owner_profile_core_id
                ),
                rejection_request_id=fabricated_commit.rejection_request_id,
                source_kind=fabricated_commit.source_kind,
                site_key=fabricated_commit.site_key,
                path=fabricated_commit.path,
                limit_kind=fabricated_commit.limit_kind,
                reservation_upper=fabricated_commit.reservation_upper,
                candidate=fabricated_commit.candidate,
                hard_cap=fabricated_commit.hard_cap,
                reason_code=fabricated_commit.reason_code,
            )
            assert committed.commit_id == fabricated_commit.commit_id

    expected_state = (
        "COMMITTED_UNACKNOWLEDGED" if active_mode == "admission" else "OPEN"
    )
    assert gate_v1.h1_attempt_rejection_gate_snapshot_v1(gate)["state"] == (
        expected_state
    )


@pytest.mark.parametrize("same_request", [True, False])
def test_admission_lease_cannot_cross_threads_or_corrupt_cursor(
    tmp_path: Path,
    same_request: bool,
) -> None:
    gate = _gate(tmp_path, f"lease-thread-{same_request}")
    errors: list[str] = []

    def commit_from_foreign_thread(lease, index: int) -> None:
        try:
            gate_v1.commit_h1_attempt_rejection_with_admission_lease_v1(
                lease,
                writer_role=gate_v1.H1AttemptRejectionWriterRoleV1.BROKER,
                decision_point_id=_id("lease-thread-decision"),
                transaction_id=_id("lease-thread-transaction"),
                shared_owner_profile_core_id=_id("lease-thread-owner"),
                rejection_request_id=_id(
                    "lease-thread-request" if same_request else f"lease-thread-{index}"
                ),
                source_kind=gate_v1.H1RejectionSourceKindV1.SHARED_OWNER,
                site_key="read:sealed-input:0",
                path="io.read_bytes",
                limit_kind=gate_v1.H1RejectionLimitKindV1.SHARED_PATH,
                reservation_upper=4,
                candidate=11 + (0 if same_request else index),
                hard_cap=10,
                reason_code="SHARED_CAP_EXHAUSTED",
            )
        except ValueError as error:
            errors.append(str(error))

    with gate_v1.hold_h1_attempt_gate_open_for_admission_v1(gate) as lease:
        threads = [
            threading.Thread(target=commit_from_foreign_thread, args=(lease, index))
            for index in range(2)
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=5)
            assert not thread.is_alive()
        assert len(errors) == 2
        assert all("owning thread" in error for error in errors)
        directory = Path(gate.gate_directory)
        assert not (directory / "intent.json").exists()
        assert not (directory / "commit.json").exists()

        committed = gate_v1.commit_h1_attempt_rejection_with_admission_lease_v1(
            lease,
            writer_role=gate_v1.H1AttemptRejectionWriterRoleV1.BROKER,
            decision_point_id=_id("lease-thread-decision"),
            transaction_id=_id("lease-thread-transaction"),
            shared_owner_profile_core_id=_id("lease-thread-owner"),
            rejection_request_id=_id("lease-thread-main-request"),
            source_kind=gate_v1.H1RejectionSourceKindV1.SHARED_OWNER,
            site_key="read:sealed-input:0",
            path="io.read_bytes",
            limit_kind=gate_v1.H1RejectionLimitKindV1.SHARED_PATH,
            reservation_upper=4,
            candidate=11,
            hard_cap=10,
            reason_code="SHARED_CAP_EXHAUSTED",
        )
        assert committed.commit_id

    assert gate_v1.h1_attempt_rejection_gate_snapshot_v1(gate)["state"] == (
        "COMMITTED_UNACKNOWLEDGED"
    )


def test_same_spec_cannot_be_initialized_under_another_base(tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    first.mkdir(mode=0o700)
    second.mkdir(mode=0o700)
    spec = _spec(first, "one-physical-base")
    gate_v1.initialize_h1_attempt_rejection_gate_v1(first, spec)
    with pytest.raises(ValueError, match="frozen physical identity"):
        gate_v1.initialize_h1_attempt_rejection_gate_v1(second, spec)
    other_spec = _spec(second, "one-physical-base")
    assert other_spec.gate_id != spec.gate_id


def test_directory_replacement_invalidates_old_and_new_handles(tmp_path: Path) -> None:
    gate = _gate(tmp_path, "inode-pinned")
    original = Path(gate.gate_directory)
    displaced = tmp_path / "displaced-gate"
    original.rename(displaced)
    original.mkdir(mode=0o700)
    with pytest.raises(ValueError, match="lacks its spec|physical allocation was already consumed"):
        gate_v1.open_h1_attempt_rejection_gate_v1(
            original,
            expected_gate_id=gate.spec.gate_id,
        )
    with pytest.raises(ValueError, match="physical allocation was already consumed"):
        gate_v1.initialize_h1_attempt_rejection_gate_v1(tmp_path, gate.spec)
    with pytest.raises(
        ValueError,
        match="physical allocation was already consumed|high-water cursor",
    ):
        gate_v1.h1_attempt_rejection_gate_snapshot_v1(gate)


def test_side_effect_guard_and_rejection_commit_have_one_kernel_order(
    tmp_path: Path,
) -> None:
    gate = _gate(tmp_path, "guard-order")
    context = multiprocessing.get_context("fork")
    entered = context.Event()
    release = context.Event()
    ready = context.Event()
    queue = context.Queue()
    guard_process = context.Process(
        target=_guard_worker,
        args=(gate.gate_directory, gate.spec.gate_id, entered, release, queue),
    )
    guard_process.start()
    assert entered.wait(timeout=10)
    commit_process = context.Process(
        target=_ready_commit_worker,
        args=(gate.gate_directory, gate.spec.gate_id, ready, queue),
    )
    commit_process.start()
    assert ready.wait(timeout=10)
    commit_process.join(timeout=0.25)
    assert commit_process.is_alive()
    release.set()
    guard_process.join(timeout=10)
    commit_process.join(timeout=10)
    assert guard_process.exitcode == 0
    assert commit_process.exitcode == 0
    results = [queue.get(timeout=5), queue.get(timeout=5)]
    assert {row[0] for row in results} == {"GUARD_RELEASED", "COMMITTED"}
    with pytest.raises(gate_v1.H1AttemptRejectedV1):
        with gate_v1.hold_h1_attempt_gate_open_for_side_effect_v1(gate):
            pass


def test_snapshot_never_mixes_open_state_with_committed_count(tmp_path: Path) -> None:
    gate = _gate(tmp_path, "atomic-snapshot")
    context = multiprocessing.get_context("fork")
    queue = context.Queue()
    process = context.Process(
        target=_concurrent_commit_worker,
        args=(gate.gate_directory, gate.spec.gate_id, 11, queue),
    )
    process.start()
    observed: list[tuple[str, int]] = []
    for _ in range(200):
        snapshot = gate_v1.h1_attempt_rejection_gate_snapshot_v1(gate)
        row = (snapshot["state"], snapshot["control_cap_rejections"])
        observed.append(row)
        assert row in {
            ("OPEN", 0),
            ("COMMITTED_UNACKNOWLEDGED", 1),
            ("ACKNOWLEDGED", 1),
        }
        if not process.is_alive():
            break
    process.join(timeout=10)
    assert process.exitcode == 0
    assert queue.get(timeout=5)[0] == "OK"
    final = gate_v1.h1_attempt_rejection_gate_snapshot_v1(gate)
    assert (final["state"], final["control_cap_rejections"]) == (
        "COMMITTED_UNACKNOWLEDGED",
        1,
    )


def test_gate_identity_transplant_and_unknown_file_fail_closed(tmp_path: Path) -> None:
    gate = _gate(tmp_path, "source")
    other = _gate(tmp_path, "other")
    with pytest.raises(ValueError, match="directory name differs"):
        gate_v1.open_h1_attempt_rejection_gate_v1(
            gate.gate_directory,
            expected_gate_id=other.spec.gate_id,
        )
    unknown = Path(gate.gate_directory) / "forged.json"
    unknown.write_bytes(b"{}")
    unknown.chmod(0o600)
    with pytest.raises(ValueError, match="unknown record"):
        gate_v1.open_h1_attempt_rejection_gate_v1(
            gate.gate_directory,
            expected_gate_id=gate.spec.gate_id,
        )


def test_gate_rejects_malformed_temp_and_cleans_strict_orphan_temp(
    tmp_path: Path,
) -> None:
    malformed_gate = _gate(tmp_path, "malformed-temp")
    malformed = Path(malformed_gate.gate_directory) / ".tmp-forged-directory"
    malformed.mkdir(mode=0o700)
    with pytest.raises(ValueError, match="unknown record"):
        gate_v1.h1_attempt_rejection_gate_snapshot_v1(malformed_gate)

    cleanable_gate = _gate(tmp_path, "strict-temp")
    orphan = Path(cleanable_gate.gate_directory) / (
        ".tmp-12345-0123456789abcdef0123456789abcdef"
    )
    orphan.write_bytes(b"orphan")
    orphan.chmod(0o600)
    gate_v1.open_h1_attempt_rejection_gate_v1(
        cleanable_gate.gate_directory,
        expected_gate_id=cleanable_gate.spec.gate_id,
    )
    assert orphan.exists(), "shared-lock validation must not perform cleanup"
    snapshot = gate_v1.h1_attempt_rejection_gate_snapshot_v1(cleanable_gate)
    assert snapshot["state"] == "OPEN"
    assert not orphan.exists()


def test_ack_without_intent_or_commit_is_rejected(tmp_path: Path) -> None:
    gate = _gate(tmp_path)
    forged = gate_v1.H1AttemptRejectionAckV1(
        gate_v1._ACK_ISSUER,
        gate.spec.gate_id,
        _id("nonexistent-commit"),
        _id("receipt"),
        _id("event"),
        _id("snapshot"),
    )
    target = Path(gate.gate_directory) / "ack.json"
    target.write_bytes(forged.canonical_bytes)
    target.chmod(0o600)
    with pytest.raises(ValueError, match="without its durable intent"):
        gate_v1.recover_h1_attempt_rejection_gate_v1(gate)


def test_orphan_commit_cannot_be_read_or_acknowledged(tmp_path: Path) -> None:
    gate = _gate(tmp_path, "orphan-commit")
    forged = gate_v1._build_commit(
        gate.spec,
        decision_point_id=_id("orphan-decision"),
        transaction_id=_id("orphan-transaction"),
        shared_owner_profile_core_id=_id("orphan-owner-core"),
        rejection_request_id=_id("orphan-request"),
        source_kind=gate_v1.H1RejectionSourceKindV1.SHARED_OWNER,
        site_key="read:sealed-input:0",
        path="io.read_bytes",
        limit_kind=gate_v1.H1RejectionLimitKindV1.SHARED_PATH,
        reservation_upper=4,
        candidate=11,
        hard_cap=10,
        reason_code="SHARED_CAP_EXHAUSTED",
    )
    target = Path(gate.gate_directory) / "commit.json"
    target.write_bytes(forged.canonical_bytes)
    target.chmod(0o600)
    with pytest.raises(ValueError, match="without its durable intent"):
        gate_v1.read_h1_attempt_rejection_commit_v1(gate)
    with pytest.raises(ValueError, match="without its durable intent"):
        gate_v1.acknowledge_h1_attempt_rejection_v1(
            gate,
            forged,
            writer_role=gate_v1.H1AttemptRejectionWriterRoleV1.BROKER,
            shared_owner_receipt_id=_id("orphan-receipt"),
            shared_owner_event_id=_id("orphan-event"),
            shared_owner_snapshot_id=_id("orphan-snapshot"),
        )
    assert not (Path(gate.gate_directory) / "ack.json").exists()


def test_lock_inode_replacement_invalidates_gate(tmp_path: Path) -> None:
    gate = _gate(tmp_path, "lock-inode")
    directory = Path(gate.gate_directory)
    lock = directory / "gate.lock"
    displaced = directory / ".tmp-displaced-lock"
    lock.rename(displaced)
    lock.write_bytes(b"ACFQP_H1_ATTEMPT_REJECTION_GATE_LOCK_V1\n")
    lock.chmod(0o600)
    with pytest.raises(ValueError, match="physical allocation was already consumed"):
        gate_v1.open_h1_attempt_rejection_gate_v1(
            directory,
            expected_gate_id=gate.spec.gate_id,
        )
    with pytest.raises(ValueError, match="physical allocation was already consumed"):
        gate_v1.h1_attempt_rejection_gate_snapshot_v1(gate)


def test_conflicting_ack_and_private_record_mutation_fail(tmp_path: Path) -> None:
    gate = _gate(tmp_path)
    commit = _commit(gate)
    gate_v1.acknowledge_h1_attempt_rejection_v1(
        gate,
        commit,
        writer_role=gate_v1.H1AttemptRejectionWriterRoleV1.BROKER,
        shared_owner_receipt_id=_id("receipt"),
        shared_owner_event_id=_id("event"),
        shared_owner_snapshot_id=_id("snapshot"),
    )
    with pytest.raises(ValueError, match="different acknowledgement"):
        gate_v1.acknowledge_h1_attempt_rejection_v1(
            gate,
            commit,
            writer_role=gate_v1.H1AttemptRejectionWriterRoleV1.BROKER,
            shared_owner_receipt_id=_id("different-receipt"),
            shared_owner_event_id=_id("event"),
            shared_owner_snapshot_id=_id("snapshot"),
        )
    object.__setattr__(commit, "hard_cap", 999)
    with pytest.raises(ValueError, match="changed after issuance"):
        _ = commit.commit_id


def test_replay_context_holds_exact_commit_and_ack_snapshot(tmp_path: Path) -> None:
    gate = _gate(tmp_path, "replay-context")
    commit = _commit(gate)
    ack = gate_v1.acknowledge_h1_attempt_rejection_v1(
        gate,
        commit,
        writer_role=gate_v1.H1AttemptRejectionWriterRoleV1.BROKER,
        shared_owner_receipt_id=_id("replay-receipt"),
        shared_owner_event_id=_id("replay-event"),
        shared_owner_snapshot_id=_id("replay-snapshot"),
    )
    with gate_v1.hold_h1_attempt_rejection_gate_for_replay_v1(gate) as replay:
        assert replay.state is gate_v1.H1AttemptRejectionGateStateV1.ACKNOWLEDGED
        assert replay.commit_id == commit.commit_id
        assert replay.commit_document == commit.to_document()
        assert replay.acknowledgement_id == ack.ack_id
        assert replay.acknowledgement_document == ack.to_document()
        with pytest.raises(ValueError, match="not serializable"):
            pickle.dumps(replay)


def test_replay_context_retains_gate_lock_until_dependent_replay_returns(
    tmp_path: Path,
) -> None:
    gate = _gate(tmp_path, "replay-lock")
    context = multiprocessing.get_context("fork")
    ready = context.Event()
    start = context.Event()
    queue = context.Queue()
    process = context.Process(
        target=_delayed_ready_commit_worker,
        args=(gate.gate_directory, gate.spec.gate_id, ready, start, queue),
    )
    process.start()
    assert ready.wait(timeout=10)
    with gate_v1.hold_h1_attempt_rejection_gate_for_replay_v1(gate) as replay:
        assert replay.state is gate_v1.H1AttemptRejectionGateStateV1.OPEN
        assert replay.commit_id is None
        assert replay.acknowledgement_id is None
        start.set()
        process.join(timeout=0.25)
        assert process.is_alive()
    process.join(timeout=10)
    assert process.exitcode == 0
    assert queue.get(timeout=5)[0] == "COMMITTED"


@pytest.mark.parametrize(
    "removed",
    [
        ("commit.json",),
        ("ack.json",),
        ("intent.json", "commit.json", "ack.json"),
    ],
)
def test_dynamic_record_deletion_cannot_lower_high_water_to_open(
    tmp_path: Path,
    removed: tuple[str, ...],
) -> None:
    gate = _gate(tmp_path, "dynamic-delete-" + "-".join(removed))
    commit = _commit(gate)
    gate_v1.acknowledge_h1_attempt_rejection_v1(
        gate,
        commit,
        writer_role=gate_v1.H1AttemptRejectionWriterRoleV1.BROKER,
        shared_owner_receipt_id=_id("delete-receipt"),
        shared_owner_event_id=_id("delete-event"),
        shared_owner_snapshot_id=_id("delete-snapshot"),
    )
    directory = Path(gate.gate_directory)
    for name in removed:
        (directory / name).unlink()
    with pytest.raises(ValueError, match="high-water|durable intent|durable commit"):
        gate_v1.recover_h1_attempt_rejection_gate_v1(gate)
    with pytest.raises(ValueError, match="high-water|durable intent|durable commit"):
        with gate_v1.hold_h1_attempt_gate_open_for_side_effect_v1(gate):
            pytest.fail("deleted durable records must not reopen side effects")
    with pytest.raises(ValueError, match="high-water|durable intent|durable commit"):
        with gate_v1.hold_h1_attempt_gate_open_for_admission_v1(gate):
            pytest.fail("deleted durable records must not reopen admission")
    with pytest.raises(ValueError, match="high-water|durable intent|durable commit"):
        with gate_v1.hold_h1_attempt_rejection_gate_for_replay_v1(gate):
            pytest.fail("deleted durable records must not replay as OPEN")


@pytest.mark.parametrize("attack", ["replace", "delete"])
def test_cursor_replacement_or_deletion_fails_closed(
    tmp_path: Path,
    attack: str,
) -> None:
    gate = _gate(tmp_path, f"cursor-{attack}")
    _commit(gate)
    directory = Path(gate.gate_directory)
    cursor = directory / "high-water.cursor"
    if attack == "replace":
        raw = cursor.read_bytes()
        cursor.rename(directory / ".tmp-displaced-cursor")
        cursor.write_bytes(raw)
        cursor.chmod(0o600)
    else:
        cursor.unlink()
    with pytest.raises(ValueError, match="cursor|physical allocation"):
        gate_v1.h1_attempt_rejection_gate_snapshot_v1(gate)
    with pytest.raises(ValueError, match="cursor|physical allocation"):
        gate_v1.open_h1_attempt_rejection_gate_v1(
            directory,
            expected_gate_id=gate.spec.gate_id,
        )


def test_deleted_base_allocation_cannot_be_recreated_by_initialize(
    tmp_path: Path,
) -> None:
    gate = _gate(tmp_path, "allocation-delete")
    base = tmp_path / ".acfqp-h1-attempt-rejection-v1"
    allocation = (
        base
        / f".acfqp-h1-attempt-slot-commit-{gate.spec.route_attempt_id}.json"
    )
    allocation.unlink()
    with pytest.raises(ValueError, match="allocation commit is absent"):
        gate_v1.initialize_h1_attempt_rejection_gate_v1(tmp_path, gate.spec)
    assert not allocation.exists()


def test_deleted_allocation_pair_cannot_reinitialize_existing_gate(
    tmp_path: Path,
) -> None:
    gate = _gate(tmp_path, "allocation-pair-delete")
    base = tmp_path / ".acfqp-h1-attempt-rejection-v1"
    (base / gate_v1._allocation_intent_name(gate.spec.route_attempt_id)).unlink()
    (base / gate_v1._allocation_commit_name(gate.spec.route_attempt_id)).unlink()
    replacement_spec = gate_v1.freeze_h1_attempt_rejection_gate_spec_v1(
        base_directory=tmp_path,
        logical_occurrence_id=gate.spec.logical_occurrence_id,
        route_attempt_id=gate.spec.route_attempt_id,
        caller_pinned_lifecycle_provenance_id=(
            gate.spec.caller_pinned_lifecycle_provenance_id
        ),
    )
    with pytest.raises(ValueError, match="allocation commit is absent"):
        gate_v1.initialize_h1_attempt_rejection_gate_v1(tmp_path, replacement_spec)
