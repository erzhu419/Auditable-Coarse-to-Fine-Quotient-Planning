"""Attack and replay tests for the V0-075 transport-only foundation."""

from __future__ import annotations

import hashlib
import inspect
from pathlib import Path
from types import SimpleNamespace

import pytest

from acfqp import v075_occurrence_cas_transport_v1 as transport


def _id(label: str) -> str:
    return hashlib.sha256(
        b"acfqp:v075-occurrence-cas-transport-test:v1\x00"
        + label.encode("utf-8")
    ).hexdigest()


def _occurrences(
    count: int = 4,
    *,
    worker: transport.RegisteredFixtureWorkerV1 = (
        transport.RegisteredFixtureWorkerV1.SAFE_HASH_V1
    ),
) -> tuple[transport.OccurrenceSpecV1, ...]:
    return tuple(
        transport.OccurrenceSpecV1(
            scientific_ordinal=index,
            occurrence_id=_id(f"occurrence-{index}"),
            target_scope_id=_id(f"target-scope-{index}"),
            target_payload={
                "fixture_label": f"fixture-{index}",
                "values": [index, index + 1, index * index],
            },
            worker_key=worker,
        )
        for index in range(count)
    )


def _prepare(
    parent: Path,
    *,
    occurrences: tuple[transport.OccurrenceSpecV1, ...] | None = None,
) -> transport.PreparedTransportBatchV1:
    return transport.prepare_transport_batch_v1(
        parent.resolve(),
        attempt_nonce_id=_id("fresh-attempt-nonce"),
        source_archive_id=_id("frozen-source-archive"),
        occurrences=_occurrences() if occurrences is None else occurrences,
    )


def test_parent_precreates_private_journals_and_freezes_plus_one_mapping(
    tmp_path: Path,
):
    prepared = _prepare(tmp_path)

    assert [item.scientific_ordinal for item in prepared.journals] == [0, 1, 2, 3]
    assert [item.transport_ordinal for item in prepared.journals] == [1, 2, 3, 4]
    assert len({item.journal_path for item in prepared.journals}) == 4
    assert all(item.journal_path.parent == prepared.batch_root for item in prepared.journals)
    assert all((item.journal_path / "chunks").is_dir() for item in prepared.journals)
    assert all((item.journal_path / "input.json").read_bytes() == item.input_bytes for item in prepared.journals)
    assert all(
        transport.ORDINAL_MAPPING.encode("utf-8") in item.input_bytes
        for item in prepared.journals
    )

    bad = (
        transport.OccurrenceSpecV1(
            scientific_ordinal=1,
            occurrence_id=_id("bad-occurrence"),
            target_scope_id=_id("bad-scope"),
            target_payload={"fixture_label": "bad", "values": [1]},
            worker_key=transport.RegisteredFixtureWorkerV1.SAFE_HASH_V1,
        ),
    )
    other_parent = tmp_path / "bad"
    other_parent.mkdir()
    with pytest.raises(
        transport.V075TransportInvariantViolation,
        match="zero-based and contiguous",
    ):
        _prepare(other_parent, occurrences=bad)


def test_serial_and_parallel_transport_artifacts_are_byte_identical_and_pid_free(
    tmp_path: Path,
):
    serial_parent = tmp_path / "serial"
    parallel_parent = tmp_path / "parallel"
    serial_parent.mkdir()
    parallel_parent.mkdir()
    serial_prepared = _prepare(serial_parent)
    parallel_prepared = _prepare(parallel_parent)

    serial = transport.run_prepared_transport_batch_v1(
        serial_prepared,
        max_workers=1,
    )
    parallel = transport.run_prepared_transport_batch_v1(
        parallel_prepared,
        max_workers=3,
    )

    assert serial.merge_id == parallel.merge_id
    assert serial.canonical_bytes == parallel.canonical_bytes
    assert [item.canonical_bytes for item in serial.occurrence_manifests] == [
        item.canonical_bytes for item in parallel.occurrence_manifests
    ]
    assert serial.physical_pid_diagnostics
    assert parallel.physical_pid_diagnostics
    assert len(
        {pid for _, pid in serial.physical_pid_diagnostics}
    ) == len(serial.occurrence_manifests)
    assert len(
        {pid for _, pid in parallel.physical_pid_diagnostics}
    ) == len(parallel.occurrence_manifests)
    assert b"pid" not in serial.canonical_bytes.lower()
    assert b"physical" not in serial.canonical_bytes.lower()
    for item in serial.occurrence_manifests:
        assert item.status == "SUCCESS"
        assert item.result_id is not None
        assert item.work_tail_unknown is False
        assert b"pid" not in item.canonical_bytes.lower()

    replayed = transport.strict_load_occurrence_manifest_v1(
        serial_prepared.journals[0].journal_path,
        expected_input_bytes=serial_prepared.journals[0].input_bytes,
        expected_input_id=serial_prepared.journals[0].input_id,
        expected_batch_id=serial_prepared.batch_id,
        returned_manifest_bytes=serial.occurrence_manifests[0].canonical_bytes,
    )
    assert replayed == serial.occurrence_manifests[0]


def test_registered_child_failure_retains_exact_work_and_never_scientifically_merges(
    tmp_path: Path,
):
    prepared = _prepare(
        tmp_path,
        occurrences=_occurrences(
            3,
            worker=(
                transport.RegisteredFixtureWorkerV1.FAIL_AFTER_SOURCE_BINDING_V1
            ),
        ),
    )

    with pytest.raises(transport.V075TransportBatchExecutionFailure) as raised:
        transport.run_prepared_transport_batch_v1(prepared, max_workers=3)

    closure = raised.value.closure
    assert len(closure.occurrence_manifests) == 3
    assert closure.work_tail_unknown is False
    assert all(item.status == "FAILURE" for item in closure.occurrence_manifests)
    assert all(
        item.failure_code == "REGISTERED_FIXTURE_FAILURE"
        for item in closure.occurrence_manifests
    )
    assert all(
        dict(item.work)["fixture.stage_checkpoints_completed"] == 3
        for item in closure.occurrence_manifests
    )
    assert b'"scientific_merge_produced":false' in closure.canonical_bytes
    assert b"pid" not in closure.canonical_bytes.lower()


def test_process_boundary_argument_is_only_canonical_bytes_and_failure_work_survives(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    captured: list[tuple[object, ...]] = []
    constructor_kwargs: list[dict[str, object]] = []

    class FailedFuture:
        def result(self):
            raise RuntimeError("synthetic process boundary loss")

    class CapturingExecutor:
        def __init__(self, **kwargs: object) -> None:
            constructor_kwargs.append(kwargs)

        def submit(self, function, *args):
            assert function is transport._execute_child_fixture_v1
            captured.append(args)
            return FailedFuture()

        def shutdown(self, **_: object) -> None:
            pass

    monkeypatch.setattr(transport, "ProcessPoolExecutor", CapturingExecutor)
    prepared = _prepare(tmp_path, occurrences=_occurrences(2))

    with pytest.raises(transport.V075TransportBatchExecutionFailure) as raised:
        transport.run_prepared_transport_batch_v1(prepared, max_workers=2)

    assert len(captured) == 2
    assert constructor_kwargs == [
        {
            "max_tasks_per_child": 1,
            "max_workers": 2,
            "mp_context": constructor_kwargs[0]["mp_context"],
        }
    ]
    assert all(tuple(type(value) for value in args) == (bytes,) for args in captured)
    assert all(
        transport.canonical_json_bytes(
            transport.loads_canonical_json(args[0])
        )
        == args[0]
        for args in captured
    )
    closure = raised.value.closure
    assert closure.work_tail_unknown is True
    assert all(
        item.failure_code == "PROCESS_BOUNDARY_FAILURE"
        for item in closure.occurrence_manifests
    )
    assert all(
        dict(item.work)["control.parent_journal_prepared"] == 1
        for item in closure.occurrence_manifests
    )
    assert all(
        dict(item.work)["control.child_submitted"] == 1
        for item in closure.occurrence_manifests
    )


def test_python310_one_shot_waves_use_fresh_process_objects_and_bound_concurrency(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    tracker = SimpleNamespace(active=0, peak=0, processes=[])

    class FakeOneShotProcess:
        def __init__(self, *, target, args) -> None:
            self.target = target
            self.args = args
            self.pid = 4242
            self.exitcode = None
            self.alive = False
            self.closed = False
            tracker.processes.append(self)

        def start(self) -> None:
            self.alive = True
            tracker.active += 1
            tracker.peak = max(tracker.peak, tracker.active)
            self.target(*self.args)
            self.exitcode = 0

        def join(self) -> None:
            if self.alive:
                self.alive = False
                tracker.active -= 1

        def is_alive(self) -> bool:
            return self.alive

        def terminate(self) -> None:
            self.exitcode = -15
            self.join()

        def close(self) -> None:
            assert not self.alive
            self.closed = True

    class FakeSpawnContext:
        Process = FakeOneShotProcess

    real_signature = inspect.signature

    def python310_signature(value):
        if value is transport.ProcessPoolExecutor:
            return SimpleNamespace(parameters={})
        return real_signature(value)

    monkeypatch.setattr(inspect, "signature", python310_signature)
    monkeypatch.setattr(transport, "get_context", lambda method: FakeSpawnContext())
    prepared = _prepare(tmp_path, occurrences=_occurrences(5))

    merge = transport.run_prepared_transport_batch_v1(prepared, max_workers=2)

    assert len(tracker.processes) == 5
    assert len({id(process) for process in tracker.processes}) == 5
    assert tracker.peak == 2
    assert tracker.active == 0
    assert all(process.closed for process in tracker.processes)
    assert all(
        tuple(type(value) for value in process.args) == (bytes,)
        for process in tracker.processes
    )
    assert all(
        transport.canonical_json_bytes(
            transport.loads_canonical_json(process.args[0])
        )
        == process.args[0]
        for process in tracker.processes
    )
    assert merge.physical_pid_diagnostics == (
        (1, 4242),
        (2, 4242),
        (3, 4242),
        (4, 4242),
        (5, 4242),
    )
    assert b"4242" not in merge.canonical_bytes
    assert b"pid" not in merge.canonical_bytes.lower()


def test_python310_join_failure_closes_manifest_and_retains_unknown_work(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    captured: list[tuple[object, ...]] = []

    class JoinFailureProcess:
        def __init__(self, *, target, args) -> None:
            assert target is transport._execute_child_fixture_v1
            captured.append(args)
            self.pid = 9090
            self.exitcode = None
            self.alive = False

        def start(self) -> None:
            self.alive = True

        def join(self) -> None:
            self.alive = False
            raise RuntimeError("synthetic join failure")

        def is_alive(self) -> bool:
            return self.alive

        def terminate(self) -> None:
            self.alive = False

        def close(self) -> None:
            assert not self.alive

    class FakeSpawnContext:
        Process = JoinFailureProcess

    real_signature = inspect.signature

    def python310_signature(value):
        if value is transport.ProcessPoolExecutor:
            return SimpleNamespace(parameters={})
        return real_signature(value)

    monkeypatch.setattr(inspect, "signature", python310_signature)
    monkeypatch.setattr(transport, "get_context", lambda method: FakeSpawnContext())
    prepared = _prepare(tmp_path, occurrences=_occurrences(2))

    with pytest.raises(transport.V075TransportBatchExecutionFailure) as raised:
        transport.run_prepared_transport_batch_v1(prepared, max_workers=1)

    assert all(tuple(type(value) for value in args) == (bytes,) for args in captured)
    closure = raised.value.closure
    assert closure.work_tail_unknown is True
    assert all(
        item.failure_code == "PROCESS_BOUNDARY_FAILURE"
        for item in closure.occurrence_manifests
    )
    assert all(
        dict(item.work)["control.child_submitted"] == 1
        for item in closure.occurrence_manifests
    )
    assert all(
        dict(item.work)["process.child_process_launches"] == 1
        for item in closure.occurrence_manifests
    )


@pytest.mark.parametrize(
    "corruption_mode",
    ("bad_chunk", "broken_chain", "extra_root"),
)
def test_malformed_child_tail_is_quarantined_and_every_journal_replays(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    corruption_mode: str,
):
    class CorruptingFuture:
        def __init__(self, request_bytes: bytes) -> None:
            self.request_bytes = request_bytes

        def result(self):
            request = transport.loads_canonical_json(self.request_bytes)
            journal = Path(request["journal_path"])
            if corruption_mode == "bad_chunk":
                (journal / "chunks" / f"{_id('malformed-cas')}.json").write_bytes(
                    b"{}"
                )
            elif corruption_mode == "broken_chain":
                checkpoint_id, raw = transport._checkpoint_document_v1(
                    request["input_document"],
                    sequence=2,
                    stage_index=0,
                    stage="INPUT_ACCEPTED",
                    previous_checkpoint_id=None,
                    event={"canonical_bytes_verified": True},
                )
                (journal / "chunks" / f"{checkpoint_id}.json").write_bytes(raw)
            else:
                (journal / "unexpected.bin").write_bytes(b"unregistered")
            raise RuntimeError(f"synthetic {corruption_mode}")

    class CorruptingExecutor:
        def __init__(self, **_: object) -> None:
            pass

        def submit(self, function, request_bytes):
            assert function is transport._execute_child_fixture_v1
            return CorruptingFuture(request_bytes)

        def shutdown(self, **_: object) -> None:
            pass

    monkeypatch.setattr(transport, "ProcessPoolExecutor", CorruptingExecutor)
    prepared = _prepare(tmp_path, occurrences=_occurrences(3))

    with pytest.raises(transport.V075TransportBatchExecutionFailure) as raised:
        transport.run_prepared_transport_batch_v1(prepared, max_workers=3)

    closure = raised.value.closure
    assert len(closure.occurrence_manifests) == len(prepared.journals)
    assert closure.work_tail_unknown is True
    assert (prepared.batch_root / "batch_failure_closure.json").is_file()
    for journal, item in zip(
        prepared.journals,
        closure.occurrence_manifests,
        strict=True,
    ):
        assert item.failure_code == "MALFORMED_CHILD_JOURNAL"
        assert item.work_tail_unknown is True
        assert (journal.journal_path / "failure_manifest.json").is_file()
        assert (journal.journal_path / "quarantine_manifest.json").is_file()
        assert (journal.journal_path / "quarantine").is_dir()
        assert not tuple((journal.journal_path / "chunks").iterdir())
        replayed = transport.strict_load_occurrence_manifest_v1(
            journal.journal_path,
            expected_input_bytes=journal.input_bytes,
            expected_input_id=journal.input_id,
            expected_batch_id=prepared.batch_id,
            returned_manifest_bytes=item.canonical_bytes,
        )
        assert replayed == item


def test_pool_start_failure_closes_every_precreated_journal_with_known_work(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    class StartFailureExecutor:
        def __init__(self, **_: object) -> None:
            raise RuntimeError("synthetic pool start failure")

    monkeypatch.setattr(transport, "ProcessPoolExecutor", StartFailureExecutor)
    prepared = _prepare(tmp_path, occurrences=_occurrences(3))

    with pytest.raises(transport.V075TransportBatchExecutionFailure) as raised:
        transport.run_prepared_transport_batch_v1(prepared, max_workers=3)

    closure = raised.value.closure
    assert closure.work_tail_unknown is False
    assert len(closure.occurrence_manifests) == 3
    for item in closure.occurrence_manifests:
        assert item.failure_code == "PROCESS_POOL_START_FAILURE"
        assert dict(item.work)["control.child_submit_attempts"] == 0
        assert dict(item.work)["control.child_submitted"] == 0
        assert dict(item.work)["process.child_process_launches"] == 0


def test_strict_loader_rejects_tampered_and_unlisted_cas_entries(tmp_path: Path):
    tamper_parent = tmp_path / "tamper"
    extra_parent = tmp_path / "extra"
    tamper_parent.mkdir()
    extra_parent.mkdir()
    tampered = _prepare(tamper_parent, occurrences=_occurrences(1))
    extra = _prepare(extra_parent, occurrences=_occurrences(1))
    tampered_merge = transport.run_prepared_transport_batch_v1(
        tampered,
        max_workers=1,
    )
    extra_merge = transport.run_prepared_transport_batch_v1(extra, max_workers=1)

    chunk_path = next((tampered.journals[0].journal_path / "chunks").iterdir())
    chunk_path.write_bytes(chunk_path.read_bytes() + b"\n")
    with pytest.raises(
        transport.V075TransportInvariantViolation,
        match="canonical JSON|identity mismatch",
    ):
        transport.strict_load_occurrence_manifest_v1(
            tampered.journals[0].journal_path,
            expected_input_bytes=tampered.journals[0].input_bytes,
            expected_input_id=tampered.journals[0].input_id,
            expected_batch_id=tampered.batch_id,
            returned_manifest_bytes=(
                tampered_merge.occurrence_manifests[0].canonical_bytes
            ),
        )

    (extra.journals[0].journal_path / "unlisted.json").write_bytes(b"{}")
    with pytest.raises(
        transport.V075TransportInvariantViolation,
        match="unlisted root files",
    ):
        transport.strict_load_occurrence_manifest_v1(
            extra.journals[0].journal_path,
            expected_input_bytes=extra.journals[0].input_bytes,
            expected_input_id=extra.journals[0].input_id,
            expected_batch_id=extra.batch_id,
            returned_manifest_bytes=extra_merge.occurrence_manifests[0].canonical_bytes,
        )


def test_no_cache_no_reuse_and_fixture_only_contract_are_enforced(tmp_path: Path):
    with pytest.raises(
        transport.V075TransportInvariantViolation,
        match="field set mismatch",
    ):
        transport.OccurrenceSpecV1(
            scientific_ordinal=0,
            occurrence_id=_id("cache-attack-occurrence"),
            target_scope_id=_id("cache-attack-scope"),
            target_payload={
                "fixture_label": "attack",
                "values": [1],
                "cached_result_id": _id("forbidden-cache"),
            },
            worker_key=transport.RegisteredFixtureWorkerV1.SAFE_HASH_V1,
        )

    prepared = _prepare(tmp_path, occurrences=_occurrences(1))
    changed = (
        transport.OccurrenceSpecV1(
            scientific_ordinal=0,
            occurrence_id=_id("occurrence-0"),
            target_scope_id=_id("target-scope-0"),
            target_payload={"fixture_label": "fixture-0", "values": [999]},
            worker_key=transport.RegisteredFixtureWorkerV1.SAFE_HASH_V1,
        ),
    )
    assert transport.derive_transport_batch_id_v1(
        attempt_nonce_id=_id("fresh-attempt-nonce"),
        source_archive_id=_id("frozen-source-archive"),
        occurrences=changed,
    ) != prepared.batch_id
    with pytest.raises(
        transport.V075TransportInvariantViolation,
        match="exclusively",
    ):
        _prepare(tmp_path, occurrences=_occurrences(1))
    assert transport.CACHE_POLICY.encode("utf-8") in prepared.journals[0].input_bytes
