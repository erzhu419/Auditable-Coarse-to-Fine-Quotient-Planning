"""Regressions for lossless frozen-source occurrence parallelism."""

from __future__ import annotations

import hashlib
import inspect
import os

import pytest

from acfqp import frozen_source_occurrence_parallel_v1 as parallel


def _id(label: str) -> str:
    return hashlib.sha256(
        b"acfqp:frozen-source-occurrence-parallel-test:v1\x00"
        + label.encode("utf-8")
    ).hexdigest()


def _archive(
    *,
    source_document: dict | None = None,
) -> parallel.FrozenSourceArchiveEnvelopeV1:
    source = (
        {
            "schema": "acfqp.safe_synthetic_source.v1",
            "feature_weights": {"adjacency": 3, "buffer": 5},
            "source_context_ids": [_id("source-a"), _id("source-b")],
        }
        if source_document is None
        else source_document
    )
    offline_work = parallel.FrozenSourceOfflineWorkV1(
        (
            ("source.accepted_draws", 18_612_224),
            ("source.kernel_transition_calls", 42),
            ("source.nonkernel_compute_events", 97),
            ("source.output_bytes", 0),
            ("source.peak_mounted_bytes", 0),
            ("source.peak_working_bytes", 0),
            ("source.process_launches", 0),
            ("source.read_bytes", 0),
            ("source.staged_bytes", 0),
        )
    )
    attestation = (
        parallel.mint_frozen_source_verification_attestation_v1(
            upstream_archive_id=_id("upstream-archive"),
            source_scope_id=_id("source-scope"),
            semantic_verifier_id=_id("semantic-verifier"),
            verification_profile_id=_id("verification-profile"),
            source_document=source,
            offline_work=offline_work,
        )
    )
    return parallel.freeze_source_archive_envelope_v1(
        upstream_archive_id=_id("upstream-archive"),
        source_scope_id=_id("source-scope"),
        source_document=source,
        offline_work=offline_work,
        verification_attestation=attestation,
    )


def _occurrences(count: int = 6) -> tuple[parallel.TargetOccurrenceSpecV1, ...]:
    return tuple(
        parallel.TargetOccurrenceSpecV1(
            ordinal=index,
            occurrence_id=_id(f"occurrence-{index}"),
            target_scope_id=_id(f"target-scope-{index}"),
            target_payload={
                "registered_index": index,
                "problem": "SAFE_SYNTHETIC",
                "values": [index, index * index],
            },
        )
        for index in range(1, count + 1)
    )


def _run(
    archive: parallel.FrozenSourceArchiveEnvelopeV1,
    *,
    max_workers: int,
    worker_key: parallel.RegisteredOccurrenceWorkerV1 = (
        parallel.RegisteredOccurrenceWorkerV1.SAFE_SYNTHETIC_HASH_V1
    ),
    occurrences: tuple[parallel.TargetOccurrenceSpecV1, ...] | None = None,
    attempt_nonce_id: str | None = None,
) -> parallel.CanonicalOccurrenceMergeV1:
    frozen_occurrences = _occurrences() if occurrences is None else occurrences
    nonce = _id("attempt-nonce") if attempt_nonce_id is None else attempt_nonce_id
    batch_id = parallel.derive_frozen_execution_batch_id_v1(
        source_archive_id=archive.archive_id,
        attempt_nonce_id=nonce,
        occurrences=frozen_occurrences,
        worker_key=worker_key,
    )
    return parallel.run_frozen_source_occurrences_v1(
        archive.canonical_bytes,
        expected_archive_id=archive.archive_id,
        expected_upstream_archive_id=archive.upstream_archive_id,
        expected_upstream_verification_id=(
            archive.upstream_verification_id
        ),
        expected_offline_work_id=archive.offline_work.work_id,
        expected_execution_batch_id=batch_id,
        attempt_nonce_id=nonce,
        occurrences=frozen_occurrences,
        worker_key=worker_key,
        max_workers=max_workers,
    )


def test_source_archive_requires_exact_external_identity_and_retains_work():
    archive = _archive()
    replayed = parallel.load_frozen_source_archive_envelope_v1(
        archive.canonical_bytes,
        expected_archive_id=archive.archive_id,
        expected_upstream_archive_id=archive.upstream_archive_id,
        expected_upstream_verification_id=(
            archive.upstream_verification_id
        ),
        expected_offline_work_id=archive.offline_work.work_id,
    )
    assert replayed == archive
    assert replayed.canonical_bytes == archive.canonical_bytes
    assert replayed.offline_work.counters == (
        ("source.accepted_draws", 18_612_224),
        ("source.kernel_transition_calls", 42),
        ("source.nonkernel_compute_events", 97),
        ("source.output_bytes", 0),
        ("source.peak_mounted_bytes", 0),
        ("source.peak_working_bytes", 0),
        ("source.process_launches", 0),
        ("source.read_bytes", 0),
        ("source.staged_bytes", 0),
    )

    with pytest.raises(
        parallel.FrozenSourceOccurrenceInvariantViolation,
        match="external identity mismatch",
    ):
        parallel.load_frozen_source_archive_envelope_v1(
            archive.canonical_bytes,
            expected_archive_id=_id("foreign-envelope"),
            expected_upstream_archive_id=archive.upstream_archive_id,
            expected_upstream_verification_id=(
                archive.upstream_verification_id
            ),
            expected_offline_work_id=archive.offline_work.work_id,
        )


def test_source_archive_rejects_byte_tamper_resigning_and_noncanonical_json():
    archive = _archive()
    tampered = archive.canonical_bytes.replace(
        b'"adjacency":3',
        b'"adjacency":4',
    )
    assert tampered != archive.canonical_bytes
    with pytest.raises(
        parallel.FrozenSourceOccurrenceInvariantViolation,
        match="mismatch",
    ):
        parallel.load_frozen_source_archive_envelope_v1(
            tampered,
            expected_archive_id=archive.archive_id,
            expected_upstream_archive_id=archive.upstream_archive_id,
            expected_upstream_verification_id=(
                archive.upstream_verification_id
            ),
            expected_offline_work_id=archive.offline_work.work_id,
        )

    resigned = _archive(
        source_document={
            "schema": "acfqp.safe_synthetic_source.v1",
            "feature_weights": {"adjacency": 4, "buffer": 5},
            "source_context_ids": [_id("source-a"), _id("source-b")],
        }
    )
    assert resigned.archive_id != archive.archive_id
    with pytest.raises(
        parallel.FrozenSourceOccurrenceInvariantViolation,
        match="external identity mismatch",
    ):
        parallel.load_frozen_source_archive_envelope_v1(
            resigned.canonical_bytes,
            expected_archive_id=archive.archive_id,
            expected_upstream_archive_id=archive.upstream_archive_id,
            expected_upstream_verification_id=(
                archive.upstream_verification_id
            ),
            expected_offline_work_id=archive.offline_work.work_id,
        )

    with pytest.raises(
        parallel.FrozenSourceOccurrenceInvariantViolation,
        match="strict canonical JSON",
    ):
        parallel.load_frozen_source_archive_envelope_v1(
            archive.canonical_bytes + b"\n",
            expected_archive_id=archive.archive_id,
            expected_upstream_archive_id=archive.upstream_archive_id,
            expected_upstream_verification_id=(
                archive.upstream_verification_id
            ),
            expected_offline_work_id=archive.offline_work.work_id,
        )


def test_parallel_and_serial_outputs_and_merge_are_byte_identical():
    archive = _archive()
    serial = _run(archive, max_workers=1)
    process_parallel = _run(archive, max_workers=3)

    assert tuple(item.canonical_bytes for item in serial.outputs) == tuple(
        item.canonical_bytes for item in process_parallel.outputs
    )
    assert serial.to_document() == process_parallel.to_document()
    assert serial.canonical_bytes == process_parallel.canonical_bytes
    assert serial.merge_id == process_parallel.merge_id
    assert serial.to_document()["source_offline_work"] == (
        archive.offline_work.to_document()
    )
    assert serial.to_document()["source_offline_work_charged_exactly_once"]
    assert serial.to_document()["target_artifact_reuse_count"] == 0
    assert [
        item["ordinal"]
        for item in serial.to_document()["occurrence_journal_entries"]
    ] == list(range(1, 7))
    assert serial.to_document()["journal_merge_complete"] is True
    assert (
        serial.to_document()["physical_completion_order_discarded"] is True
    )
    assert "max_workers" not in serial.to_document()
    assert len(serial.child_journals) == 6
    assert serial.to_document()["unknown_work_tail_count"] == 0
    assert serial.to_document()["aggregate_known_child_work"] == [
        {"counter": "control.child_completed", "value": 6},
        {"counter": "control.child_failed", "value": 0},
        {"counter": "control.child_submit_attempts", "value": 6},
        {"counter": "control.child_submitted", "value": 6},
        {"counter": "process.child_process_launches", "value": 6},
        {"counter": "synthetic.registered_worker_events", "value": 6},
    ]
    assert len(set(serial.diagnostic_child_pids)) == 6
    assert len(set(process_parallel.diagnostic_child_pids)) == 6
    assert os.getpid() not in serial.diagnostic_child_pids
    assert os.getpid() not in process_parallel.diagnostic_child_pids
    assert "diagnostic_child_pids" not in serial.to_document()
    assert str(os.getpid()).encode("ascii") not in serial.canonical_bytes


def _caught_failure(
    archive: parallel.FrozenSourceArchiveEnvelopeV1,
    *,
    max_workers: int,
    worker_key: parallel.RegisteredOccurrenceWorkerV1,
    occurrences: tuple[parallel.TargetOccurrenceSpecV1, ...],
) -> parallel.FrozenSourceOccurrenceExecutionFailure:
    caught: pytest.ExceptionInfo[
        parallel.FrozenSourceOccurrenceExecutionFailure
    ]
    with pytest.raises(
        parallel.FrozenSourceOccurrenceExecutionFailure
    ) as caught:
        _run(
            archive,
            max_workers=max_workers,
            worker_key=worker_key,
            occurrences=occurrences,
        )
    return caught.value


def test_all_child_failures_are_retained_in_byte_identical_closures() -> None:
    archive = _archive()
    worker = (
        parallel.RegisteredOccurrenceWorkerV1.SAFE_SYNTHETIC_FAIL_V1
    )
    serial = _caught_failure(
        archive,
        max_workers=1,
        worker_key=worker,
        occurrences=_occurrences(3),
    )
    process_parallel = _caught_failure(
        archive,
        max_workers=3,
        worker_key=worker,
        occurrences=_occurrences(3),
    )
    assert serial.occurrence_ordinal == 1
    assert serial.occurrence_id == _id("occurrence-1")
    assert serial.failure_closure_bytes == (
        process_parallel.failure_closure_bytes
    )
    assert serial.failure_closure_id == process_parallel.failure_closure_id
    closure = serial.failure_closure
    assert [item.ordinal for item in closure.child_journals] == [1, 2, 3]
    assert len(closure.completed_attempts) == 0
    assert len(closure.failed_attempts) == 3
    assert closure.to_document()["launched_child_count"] == 3
    assert closure.to_document()["aggregate_known_child_work"] == [
        {"counter": "control.child_completed", "value": 0},
        {"counter": "control.child_failed", "value": 3},
        {"counter": "control.child_submit_attempts", "value": 3},
        {"counter": "control.child_submitted", "value": 3},
        {"counter": "process.child_process_launches", "value": 3},
        {"counter": "synthetic.registered_worker_events", "value": 3},
    ]
    assert not hasattr(serial, "partial_outputs_discarded")
    assert serial.partial_outputs_retained_for_accounting is True
    assert serial.partial_outputs_scientifically_merged is False


def test_later_child_failure_retains_all_work_without_scientific_merge() -> None:
    archive = _archive()
    base = list(_occurrences(3))
    base[1] = parallel.TargetOccurrenceSpecV1(
        ordinal=2,
        occurrence_id=_id("occurrence-2"),
        target_scope_id=_id("target-scope-2"),
        target_payload={"synthetic_failure": True},
    )
    worker = (
        parallel.RegisteredOccurrenceWorkerV1
        .SAFE_SYNTHETIC_MARKED_FAILURE_V1
    )
    serial = _caught_failure(
        archive,
        max_workers=1,
        worker_key=worker,
        occurrences=tuple(base),
    )
    process_parallel = _caught_failure(
        archive,
        max_workers=3,
        worker_key=worker,
        occurrences=tuple(base),
    )
    assert serial.occurrence_ordinal == 2
    assert serial.occurrence_id == _id("occurrence-2")
    assert serial.failure_closure_bytes == (
        process_parallel.failure_closure_bytes
    )
    closure = serial.failure_closure
    assert [item.ordinal for item in closure.child_journals] == [1, 2, 3]
    assert [item.ordinal for item in closure.completed_attempts] == [1, 3]
    assert [item.ordinal for item in closure.failed_attempts] == [2]
    document = closure.to_document()
    assert document["completed_child_count"] == 2
    assert document["failed_child_count"] == 1
    assert len(document["completed_output_ids"]) == 2
    assert document["scientific_occurrence_merge"] == {
        "kind": "NOT_PRODUCED_DUE_TO_CHILD_FAILURE"
    }
    assert document["scientific_merge_authority"] is False
    assert document["aggregate_known_child_work"] == [
        {"counter": "control.child_completed", "value": 2},
        {"counter": "control.child_failed", "value": 1},
        {"counter": "control.child_submit_attempts", "value": 3},
        {"counter": "control.child_submitted", "value": 3},
        {"counter": "process.child_process_launches", "value": 3},
        {"counter": "synthetic.registered_worker_events", "value": 3},
    ]

    replayed = parallel.load_occurrence_failure_closure_v1(
        closure.canonical_bytes,
        source_archive=archive,
        occurrence_inputs=closure.inputs,
        expected_failure_closure_id=closure.failure_closure_id,
    )
    assert replayed == closure
    assert replayed.canonical_bytes == closure.canonical_bytes


def test_failure_closure_strict_loader_rejects_tamper_and_foreign_id() -> None:
    archive = _archive()
    failure = _caught_failure(
        archive,
        max_workers=1,
        worker_key=(
            parallel.RegisteredOccurrenceWorkerV1.SAFE_SYNTHETIC_FAIL_V1
        ),
        occurrences=_occurrences(2),
    )
    closure = failure.failure_closure
    tampered = closure.canonical_bytes.replace(
        b'"failed_child_count":2',
        b'"failed_child_count":1',
    )
    assert tampered != closure.canonical_bytes
    with pytest.raises(
        parallel.FrozenSourceOccurrenceInvariantViolation,
        match="content replay mismatch",
    ):
        parallel.load_occurrence_failure_closure_v1(
            tampered,
            source_archive=archive,
            occurrence_inputs=closure.inputs,
            expected_failure_closure_id=closure.failure_closure_id,
        )
    with pytest.raises(
        parallel.FrozenSourceOccurrenceInvariantViolation,
        match="content replay mismatch",
    ):
        parallel.load_occurrence_failure_closure_v1(
            closure.canonical_bytes,
            source_archive=archive,
            occurrence_inputs=closure.inputs,
            expected_failure_closure_id=_id("foreign-failure-closure"),
        )


def test_target_identity_in_source_archive_is_rejected_before_execution():
    target_id = _id("occurrence-1")
    archive = _archive(
        source_document={
            "schema": "acfqp.safe_synthetic_source.v1",
            "illegally_embedded_target_occurrence": target_id,
        }
    )
    with pytest.raises(
        parallel.FrozenSourceOccurrenceInvariantViolation,
        match="contains a registered target identity",
    ):
        _run(archive, max_workers=1, occurrences=_occurrences(2))


def test_source_archive_defensively_freezes_caller_mapping() -> None:
    source_document = {
        "schema": "acfqp.safe_synthetic_source.v1",
        "nested": {"proposal": "frozen"},
    }
    archive = _archive(source_document=source_document)
    frozen_bytes = archive.canonical_bytes
    frozen_id = archive.archive_id
    source_document["nested"]["proposal"] = "mutated"
    source_document["late_target"] = _id("occurrence-1")
    assert archive.canonical_bytes == frozen_bytes
    assert archive.archive_id == frozen_id
    assert archive.sealed_source_document == {
        "nested": {"proposal": "frozen"},
        "schema": "acfqp.safe_synthetic_source.v1",
    }
    result = _run(archive, max_workers=1, occurrences=_occurrences(2))
    assert result.source_archive.archive_id == frozen_id


def test_schedule_and_api_forbid_result_reuse_and_unbounded_workers():
    parameters = inspect.signature(
        parallel.run_frozen_source_occurrences_v1
    ).parameters
    assert not {
        "prior_outputs",
        "target_cache",
        "resume",
        "reuse",
    } & set(parameters)

    archive = _archive()
    changed_order = tuple(reversed(_occurrences(3)))
    with pytest.raises(
        parallel.FrozenSourceOccurrenceInvariantViolation,
        match="contiguous in registered order",
    ):
        _run(archive, max_workers=1, occurrences=changed_order)
    with pytest.raises(
        parallel.FrozenSourceOccurrenceInvariantViolation,
        match="outside the frozen",
    ):
        _run(archive, max_workers=parallel.MAX_WORKERS + 1)


def test_target_and_result_payloads_are_deeply_sealed() -> None:
    archive = _archive()
    caller_payload = {"nested": {"value": 1}, "values": [1, 2]}
    occurrence = parallel.TargetOccurrenceSpecV1(
        ordinal=1,
        occurrence_id=_id("sealed-occurrence"),
        target_scope_id=_id("sealed-target-scope"),
        target_payload=caller_payload,
    )
    caller_payload["nested"]["value"] = 9
    occurrence.target_payload["nested"]["value"] = 8
    assert occurrence.sealed_target_payload["nested"]["value"] == 1
    result = _run(
        archive,
        max_workers=1,
        occurrences=(occurrence,),
        attempt_nonce_id=_id("sealed-attempt"),
    )
    frozen = (
        result.inputs[0].input_id,
        result.outputs[0].output_id,
        result.merge_id,
        result.canonical_bytes,
    )
    result.inputs[0].target_payload["nested"]["value"] = 7
    result.outputs[0].result_payload["target_payload"]["nested"]["value"] = 6
    assert (
        result.inputs[0].input_id,
        result.outputs[0].output_id,
        result.merge_id,
        result.canonical_bytes,
    ) == frozen


def test_recursive_transport_smuggling_and_unregistered_counter_fail() -> None:
    with pytest.raises(
        parallel.FrozenSourceOccurrenceInvariantViolation,
        match="forbidden cache/reuse/result key",
    ):
        _archive(
            source_document={
                "schema": "acfqp.safe_synthetic_source.v1",
                "nested": {"post-target-cache": {"value": 1}},
            }
        )
    with pytest.raises(
        parallel.FrozenSourceOccurrenceInvariantViolation,
        match="forbidden cache/reuse/result key",
    ):
        parallel.TargetOccurrenceSpecV1(
            ordinal=1,
            occurrence_id=_id("smuggled-occurrence"),
            target_scope_id=_id("smuggled-target-scope"),
            target_payload={"nested": [{"prior_outputs": [1]}]},
        )
    with pytest.raises(
        parallel.FrozenSourceOccurrenceInvariantViolation,
        match="complete registered counter vocabulary",
    ):
        parallel.FrozenSourceOfflineWorkV1((("invented.counter", 1),))
    archive = _archive()
    source_alias = parallel.TargetOccurrenceSpecV1(
        ordinal=1,
        occurrence_id=_id("source-alias-occurrence"),
        target_scope_id=_id("source-alias-scope"),
        target_payload={"foreign_scope": archive.source_scope_id},
    )
    with pytest.raises(
        parallel.FrozenSourceOccurrenceInvariantViolation,
        match="contains a registered source identity",
    ):
        _run(
            archive,
            max_workers=1,
            occurrences=(source_alias,),
            attempt_nonce_id=_id("source-alias-attempt"),
        )


def test_batch_nonce_binds_attempt_without_claiming_global_nonce_registry() -> None:
    archive = _archive()
    occurrences = _occurrences(2)
    first = _run(
        archive,
        max_workers=2,
        occurrences=occurrences,
        attempt_nonce_id=_id("attempt-A"),
    )
    replay = _run(
        archive,
        max_workers=1,
        occurrences=occurrences,
        attempt_nonce_id=_id("attempt-A"),
    )
    second = _run(
        archive,
        max_workers=2,
        occurrences=occurrences,
        attempt_nonce_id=_id("attempt-B"),
    )
    assert first.canonical_bytes == replay.canonical_bytes
    assert first.merge_id != second.merge_id
    assert (
        first.to_document()["global_nonce_uniqueness_claimed"] is False
    )
    assert first.to_document()["execution_recomputed_without_cache"] is True


def test_process_start_and_submit_failures_have_stable_complete_closures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    archive = _archive()

    class StartFailure:
        calls = 0

        def __init__(self, **_kwargs):
            type(self).calls += 1
            raise OSError(
                f"/tmp/pid-{os.getpid()}-volatile-{type(self).calls}"
            )

    monkeypatch.setattr(parallel, "ProcessPoolExecutor", StartFailure)
    first = _caught_failure(
        archive,
        max_workers=2,
        worker_key=(
            parallel.RegisteredOccurrenceWorkerV1.SAFE_SYNTHETIC_HASH_V1
        ),
        occurrences=_occurrences(3),
    )
    second = _caught_failure(
        archive,
        max_workers=2,
        worker_key=(
            parallel.RegisteredOccurrenceWorkerV1.SAFE_SYNTHETIC_HASH_V1
        ),
        occurrences=_occurrences(3),
    )
    assert first.failure_closure_bytes == second.failure_closure_bytes
    document = first.failure_closure.to_document()
    assert document["scheduled_child_count"] == 3
    assert document["submitted_child_count"] == 0
    assert document["launched_child_count"] == 0
    assert document["unknown_work_tail_count"] == 0
    assert {
        item.failure_code
        for item in first.failure_closure.failed_attempts
    } == {"PROCESS_POOL_START_FAILURE"}
    assert b"/tmp/" not in first.failure_closure_bytes

    class SubmitFailure:
        def __init__(self, **_kwargs):
            pass

        def submit(self, *_args, **_kwargs):
            raise OSError(f"submit pid={os.getpid()} /volatile/path")

        def shutdown(self, **_kwargs):
            return None

    monkeypatch.setattr(parallel, "ProcessPoolExecutor", SubmitFailure)
    failed_submit = _caught_failure(
        archive,
        max_workers=2,
        worker_key=(
            parallel.RegisteredOccurrenceWorkerV1.SAFE_SYNTHETIC_HASH_V1
        ),
        occurrences=_occurrences(3),
    ).failure_closure
    assert [item.failure_code for item in failed_submit.child_journals] == [
        "PROCESS_SUBMIT_FAILURE",
        "BATCH_ABORTED_BEFORE_SUBMIT",
        "BATCH_ABORTED_BEFORE_SUBMIT",
    ]
    assert failed_submit.to_document()["submitted_child_count"] == 0
    assert failed_submit.to_document()["launched_child_count"] == 0

    class VolatileBoundaryFuture:
        calls = 0

        def result(self):
            type(self).calls += 1
            raise OSError(
                f"worker pid={os.getpid()} path=/volatile/{type(self).calls}"
            )

    class BoundaryFailure:
        def __init__(self, **_kwargs):
            pass

        def submit(self, *_args, **_kwargs):
            return VolatileBoundaryFuture()

        def shutdown(self, **_kwargs):
            return None

    monkeypatch.setattr(parallel, "ProcessPoolExecutor", BoundaryFailure)
    boundary_first = _caught_failure(
        archive,
        max_workers=2,
        worker_key=(
            parallel.RegisteredOccurrenceWorkerV1.SAFE_SYNTHETIC_HASH_V1
        ),
        occurrences=_occurrences(2),
    )
    boundary_second = _caught_failure(
        archive,
        max_workers=2,
        worker_key=(
            parallel.RegisteredOccurrenceWorkerV1.SAFE_SYNTHETIC_HASH_V1
        ),
        occurrences=_occurrences(2),
    )
    assert boundary_first.failure_closure_bytes == (
        boundary_second.failure_closure_bytes
    )
    assert (
        boundary_first.failure_closure.to_document()["unknown_work_tail_count"]
        == 2
    )
    assert (
        boundary_first.failure_closure.to_document()[
            "all_launched_child_journals_retained"
        ]
        is False
    )
    assert (
        boundary_first.failure_closure.to_document()[
            "all_available_child_journals_retained"
        ]
        is True
    )
    assert {
        item.failure_code
        for item in boundary_first.failure_closure.failed_attempts
    } == {"PROCESS_BOUNDARY_FAILURE"}
    assert b"/volatile/" not in boundary_first.failure_closure_bytes


def test_legal_near_cap_payload_generates_replayable_output_and_journal() -> None:
    archive = _archive()
    occurrence = parallel.TargetOccurrenceSpecV1(
        ordinal=1,
        occurrence_id=_id("near-cap-occurrence"),
        target_scope_id=_id("near-cap-scope"),
        target_payload={"blob": "x" * 60_000},
    )
    result = _run(
        archive,
        max_workers=1,
        occurrences=(occurrence,),
        attempt_nonce_id=_id("near-cap-attempt"),
    )
    replayed_output = parallel.load_occurrence_output_v1(
        result.outputs[0].canonical_bytes,
        occurrence_input=result.inputs[0],
    )
    replayed_journal = parallel.load_child_attempt_journal_v1(
        result.child_journals[0].canonical_bytes,
        occurrence_input=result.inputs[0],
    )
    assert replayed_output.output_id == result.outputs[0].output_id
    assert replayed_journal.journal_id == result.child_journals[0].journal_id
    assert (
        len(result.outputs[0].canonical_bytes)
        <= parallel.MAX_OCCURRENCE_OUTPUT_BYTES
    )
    replayed_merge = parallel.load_canonical_occurrence_merge_v1(
        result.canonical_bytes,
        source_archive=archive,
        occurrence_inputs=result.inputs,
        expected_merge_id=result.merge_id,
    )
    assert replayed_merge.canonical_bytes == result.canonical_bytes
    assert (
        len(result.canonical_bytes)
        <= parallel.MAX_COMPOSITE_ARTIFACT_BYTES
    )


def test_output_and_child_journal_reject_counter_injection_or_mismatch() -> None:
    archive = _archive()
    result = _run(
        archive,
        max_workers=1,
        occurrences=_occurrences(1),
        attempt_nonce_id=_id("counter-attack-attempt"),
    )
    output = result.outputs[0]
    with pytest.raises(
        parallel.FrozenSourceOccurrenceInvariantViolation,
        match="exact registered worker-counter vocabulary",
    ):
        parallel.OccurrenceOutputV1(
            occurrence_input_id=output.occurrence_input_id,
            ordinal=output.ordinal,
            occurrence_id=output.occurrence_id,
            target_scope_id=output.target_scope_id,
            source_archive_id=output.source_archive_id,
            execution_batch_id=output.execution_batch_id,
            attempt_nonce_id=output.attempt_nonce_id,
            worker_key=output.worker_key,
            result_payload=output.sealed_result_payload,
            online_work=(("unregistered.worker.counter", 1),),
        )
    journal = result.child_journals[0]
    tampered_work = tuple(
        (name, 0 if name == "synthetic.registered_worker_events" else value)
        for name, value in journal.work_counters
    )
    with pytest.raises(
        parallel.FrozenSourceOccurrenceInvariantViolation,
        match="inconsistent output",
    ):
        parallel.ChildAttemptJournalV1(
            occurrence_input_id=journal.occurrence_input_id,
            ordinal=journal.ordinal,
            occurrence_id=journal.occurrence_id,
            target_scope_id=journal.target_scope_id,
            source_archive_id=journal.source_archive_id,
            worker_key=journal.worker_key,
            status=journal.status,
            output=journal.output,
            failure_code=None,
            failure_kind=None,
            failure_message_sha256=None,
            work_counters=tampered_work,
            work_tail_unknown=False,
        )


def test_strict_success_merge_loader_rejects_nested_tamper_and_foreign_id() -> None:
    archive = _archive()
    result = _run(
        archive,
        max_workers=2,
        occurrences=_occurrences(3),
        attempt_nonce_id=_id("strict-merge-attempt"),
    )
    replayed = parallel.load_canonical_occurrence_merge_v1(
        result.canonical_bytes,
        source_archive=archive,
        occurrence_inputs=result.inputs,
        expected_merge_id=result.merge_id,
    )
    assert replayed == result
    document = parallel.loads_canonical_json(result.canonical_bytes)
    document["occurrence_outputs"][0]["online_work"][0]["value"] = 2
    tampered = parallel.canonical_json_bytes(document)
    with pytest.raises(
        parallel.FrozenSourceOccurrenceInvariantViolation,
        match="mismatch",
    ):
        parallel.load_canonical_occurrence_merge_v1(
            tampered,
            source_archive=archive,
            occurrence_inputs=result.inputs,
            expected_merge_id=result.merge_id,
        )
    with pytest.raises(
        parallel.FrozenSourceOccurrenceInvariantViolation,
        match="mismatch",
    ):
        parallel.load_canonical_occurrence_merge_v1(
            result.canonical_bytes,
            source_archive=archive,
            occurrence_inputs=result.inputs,
            expected_merge_id=_id("foreign-merge"),
        )


def test_composite_cap_formula_and_multi_occurrence_near_cap_success() -> None:
    assert parallel.MAX_COMPOSITE_ARTIFACT_BYTES == (
        parallel.MAX_COMPOSITE_FIXED_OVERHEAD_BYTES
        + parallel.MAX_OCCURRENCES
        * (
            parallel.MAX_CHILD_JOURNAL_BYTES
            + parallel.MAX_OCCURRENCE_OUTPUT_BYTES
            + parallel.MAX_COMPOSITE_PER_OCCURRENCE_OVERHEAD_BYTES
        )
    )
    archive = _archive()
    occurrences = tuple(
        parallel.TargetOccurrenceSpecV1(
            ordinal=index,
            occurrence_id=_id(f"multi-cap-occurrence-{index}"),
            target_scope_id=_id(f"multi-cap-scope-{index}"),
            target_payload={"blob": "x" * 60_000, "index": index},
        )
        for index in range(1, 9)
    )
    result = _run(
        archive,
        max_workers=4,
        occurrences=occurrences,
        attempt_nonce_id=_id("multi-cap-attempt"),
    )
    assert len(result.outputs) == 8
    assert all(
        len(value.canonical_bytes) <= parallel.MAX_OCCURRENCE_OUTPUT_BYTES
        for value in result.outputs
    )
    assert all(
        len(value.canonical_bytes) <= parallel.MAX_CHILD_JOURNAL_BYTES
        for value in result.child_journals
    )
    assert (
        len(result.canonical_bytes)
        <= parallel.MAX_COMPOSITE_ARTIFACT_BYTES
    )
    replayed = parallel.load_canonical_occurrence_merge_v1(
        result.canonical_bytes,
        source_archive=archive,
        occurrence_inputs=result.inputs,
        expected_merge_id=result.merge_id,
    )
    assert replayed.canonical_bytes == result.canonical_bytes


def test_result_payload_and_output_envelope_caps_are_separate_and_closed() -> None:
    archive = _archive()
    base = _run(
        archive,
        max_workers=1,
        occurrences=_occurrences(1),
        attempt_nonce_id=_id("output-cap-attempt"),
    )
    bound = base.inputs[0]
    near_limit = parallel.OccurrenceOutputV1(
        occurrence_input_id=bound.input_id,
        ordinal=bound.ordinal,
        occurrence_id=bound.occurrence_id,
        target_scope_id=bound.target_scope_id,
        source_archive_id=bound.source_archive_id,
        execution_batch_id=bound.execution_batch_id,
        attempt_nonce_id=bound.attempt_nonce_id,
        worker_key=bound.worker_key,
        result_payload={
            "blob": "x"
            * (parallel.MAX_OCCURRENCE_RESULT_PAYLOAD_BYTES - 2_048)
        },
        online_work=(("synthetic.registered_worker_events", 1),),
    )
    assert len(near_limit.canonical_bytes) <= parallel.MAX_OCCURRENCE_OUTPUT_BYTES
    assert (
        parallel.load_occurrence_output_v1(
            near_limit.canonical_bytes,
            occurrence_input=bound,
        ).output_id
        == near_limit.output_id
    )
    near_limit_journal = parallel.ChildAttemptJournalV1(
        occurrence_input_id=bound.input_id,
        ordinal=bound.ordinal,
        occurrence_id=bound.occurrence_id,
        target_scope_id=bound.target_scope_id,
        source_archive_id=bound.source_archive_id,
        worker_key=bound.worker_key,
        status=parallel.ChildAttemptStatusV1.COMPLETED,
        output=near_limit,
        failure_code=None,
        failure_kind=None,
        failure_message_sha256=None,
        work_counters=(
            ("control.child_completed", 1),
            ("control.child_failed", 0),
            ("control.child_submit_attempts", 1),
            ("control.child_submitted", 1),
            ("process.child_process_launches", 1),
            ("synthetic.registered_worker_events", 1),
        ),
        work_tail_unknown=False,
    )
    assert (
        len(near_limit_journal.canonical_bytes)
        <= parallel.MAX_CHILD_JOURNAL_BYTES
    )
    with pytest.raises(
        parallel.FrozenSourceOccurrenceInvariantViolation,
        match="occurrence result exceeds",
    ):
        parallel.OccurrenceOutputV1(
            occurrence_input_id=bound.input_id,
            ordinal=bound.ordinal,
            occurrence_id=bound.occurrence_id,
            target_scope_id=bound.target_scope_id,
            source_archive_id=bound.source_archive_id,
            execution_batch_id=bound.execution_batch_id,
            attempt_nonce_id=bound.attempt_nonce_id,
            worker_key=bound.worker_key,
            result_payload={
                "blob": "x"
                * parallel.MAX_OCCURRENCE_RESULT_PAYLOAD_BYTES
            },
            online_work=(("synthetic.registered_worker_events", 1),),
        )
