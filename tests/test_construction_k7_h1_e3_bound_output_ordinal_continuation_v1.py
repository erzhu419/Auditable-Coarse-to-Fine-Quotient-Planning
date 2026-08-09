from __future__ import annotations

import copy
import errno
import gc
import inspect
import os
from pathlib import Path
import tempfile
import threading

import pytest

from acfqp import accounting_v1
from acfqp import actual_accounting_v1
from acfqp import construction_k7_h1_cleanup_action_journal_v1 as e2_v1
from acfqp import construction_k7_h1_domain_registry_extension_v8 as domains_v8
from acfqp import construction_k7_h1_domain_registry_extension_v9 as domains_v9
from acfqp import construction_k7_h1_domain_registry_extension_v10 as domains_v10
from acfqp import construction_k7_h1_domain_registry_extension_v11 as domains_v11
from acfqp import construction_k7_h1_e3_bound_output_ordinal_continuation_v1 as e4_v1
from acfqp import construction_k7_h1_exclusive_native_resource_broker_v1 as e3_v1
from acfqp import construction_k7_h1_native_capability_guardian_v1 as e1_v1
from acfqp import routing_v1
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_H1_JOINT_OUTPUT_READ_FIXED_POINT_V1_DOMAIN,
    CONSTRUCTION_K7_H1_JOINT_OUTPUT_READ_ITERATION_V1_DOMAIN,
    canonical_json_bytes,
)


@pytest.fixture
def tmp_path() -> Path:
    """E4 requires native Unix mode/inode semantics; DrvFS is not admissible."""

    with tempfile.TemporaryDirectory(prefix="acfqp-e4-test-", dir="/tmp") as root:
        yield Path(root)


def _id(label: str) -> str:
    import hashlib

    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _prepare(tmp_path: Path) -> e4_v1.H1E3BoundOutputContinuationContextV1:
    return e4_v1.prepare_h1_e3_bound_output_continuation_context_v1(
        output_parent_directory=tmp_path,
        caller_binding_id=_id("caller"),
        lifecycle_snapshot={
            "schema": "acfqp.test.e4.lifecycle_snapshot.nonformal.v1",
            "state": "BEFORE_E3",
            "formal_authority_present": False,
        },
        lifecycle_program={
            "schema": "acfqp.test.e4.lifecycle_program.nonformal.v1",
            "remaining_ordinals": list(range(41, 63)),
            "formal_v7_authority_present": False,
        },
        logical_occurrence_id=_id("occurrence"),
        route_attempt_id=_id("attempt"),
        read_bytes_base=17,
    )


def _synthetic_admitted_completion() -> dict[str, object]:
    return {
        "h1_exclusive_broker_completion_id": _id("synthetic-e3-completion"),
        "session_nonce": _id("synthetic-e3-session"),
    }


def _run_internal_success(
    tmp_path: Path,
) -> tuple[
    e4_v1.H1E3BoundOutputContinuationContextV1,
    e4_v1.H1E3BoundOutputCompletionV1,
]:
    context = _prepare(tmp_path)
    context_document = e4_v1._verify_live_context(  # noqa: SLF001
        context, require_empty=True
    )
    result = e4_v1._run_admitted_output_program(  # noqa: SLF001
        context=context,
        context_document=context_document,
        e3_completion=_synthetic_admitted_completion(),
        fault=e4_v1.H1E4FaultInjectionV1.NONE,
    )
    assert type(result) is e4_v1.H1E3BoundOutputCompletionV1
    return context, result


def test_v11_is_additive_disjoint_and_reuses_only_exact_joint_domains() -> None:
    assert not (
        domains_v11.K7_H1_DOMAIN_TAG_EXTENSION_V11
        & domains_v8.K7_H1_DOMAIN_TAG_EXTENSION_V8
    )
    assert not (
        domains_v11.K7_H1_DOMAIN_TAG_EXTENSION_V11
        & domains_v9.K7_H1_DOMAIN_TAG_EXTENSION_V9
    )
    assert not (
        domains_v11.K7_H1_DOMAIN_TAG_EXTENSION_V11
        & domains_v10.K7_H1_DOMAIN_TAG_EXTENSION_V10
    )
    assert len(domains_v11.K7_H1_DOMAIN_TAG_EXTENSION_REGISTRY_V11) == 14
    assert (
        domains_v11.CONSTRUCTION_K7_H1_JOINT_OUTPUT_READ_ITERATION_V1_DOMAIN
        == CONSTRUCTION_K7_H1_JOINT_OUTPUT_READ_ITERATION_V1_DOMAIN
    )
    assert (
        domains_v11.CONSTRUCTION_K7_H1_JOINT_OUTPUT_READ_FIXED_POINT_V1_DOMAIN
        == CONSTRUCTION_K7_H1_JOINT_OUTPUT_READ_FIXED_POINT_V1_DOMAIN
    )
    with pytest.raises(ValueError, match="absent"):
        domains_v11.extension_content_id_v11(
            domains_v10.CONSTRUCTION_K7_H1_EXCLUSIVE_BROKER_COMPLETION_V1_DOMAIN,
            {"schema": "acfqp.test.foreign.v1"},
        )


def test_profile_freezes_exact_eight_roles_ordinals_limits_and_all_locks() -> None:
    document = e4_v1.official_h1_e3_bound_output_continuation_profile_v1().to_document()
    assert document["proposed_contract_version"] == "2.0.59-E-C-E4"
    assert document["profile_key"] == (
        "construction_k7_h1_e3_bound_output_ordinal_continuation_v1"
    )
    assert document["accepted_upstream_type"] == "H1ExclusiveBrokerCompletionV1"
    assert document["accepted_upstream_disposition"] == "BROKER_EXCLUSIVE_PRESENT"
    assert document["typed_null_prebinding_accepted"] is False
    assert [row["role"] for row in document["role_ordinal_file_map"]] == list(
        e4_v1.ROLE_ORDER
    )
    assert [row["normal_ordinal"] for row in document["role_ordinal_file_map"]] == list(
        range(53, 61)
    )
    assert document["durable_role_count"] == 8
    assert document["ninth_durable_wrapper_forbidden"] is True
    assert document["fixed_point_iteration_cap"] == 32
    assert document["role_byte_cap"] == 256 * 1024
    assert document["total_output_byte_cap"] == 2 * 1024 * 1024
    assert document["serializer_buffer_extent_is_not_peak_working_memory"] is True
    assert document["maximum_simultaneous_render_sets"] == 2
    assert document["pinned_parent_directory_fd_required"] is True
    assert document["parent_entry_fsync_after_mkdir_required"] is True
    assert document["unified_owned_fd_registry_required"] is True
    assert document["fork_covers_precontext_and_runtime_role_fds"] is True
    assert document["persistent_close_failure_quarantined_and_retryable"] is True
    assert document["authoritative_full_completion_reconstruction_required"] is True
    assert document["route_wide_peak_authority_present"] is False
    assert document["peak_scope_status"] == "PEAK_SCOPE_UNRESOLVED"
    assert document["formal_counter_records_issued"] is False
    assert document["formal_work_vector_issued"] is False
    assert document["formal_comparison_vector_issued"] is False
    assert document["current_access_authority_present"] is False
    assert document["formal_v7_authority_present"] is False
    assert document["official_execution_allowed"] is False
    assert document["official_scalar_cost"] is None
    assert document["official_N_break_even"] is None
    assert document["COUNTER_COMPLETENESS_GATE"] == "NOT_RUN"
    assert document["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"


def test_context_is_nonce_bound_retained_nonformal_and_fresh_inode_pinned(
    tmp_path: Path,
) -> None:
    context = _prepare(tmp_path)
    try:
        document = context.to_document()
        assert len(document["context_nonce"]) == 64
        assert document["nonformal_lifecycle_snapshot"]["formal_authority_present"] is False
        assert document["nonformal_lifecycle_program"]["formal_authority_present"] is False
        assert document["output_directory"]["fresh_empty_at_preparation"] is True
        assert document["output_directory"]["pinned_directory_fd_retained"] is True
        assert document["output_directory"]["pinned_parent_directory_fd_retained"] is True
        assert document["output_directory"]["parent_entry_fsync_complete"] is True
        assert document["read_bytes_base"] == 17
        assert os.listdir(context._directory_fd) == []  # noqa: SLF001
        assert context._directory_path.parent == tmp_path.resolve()  # noqa: SLF001
        assert e4_v1._verify_live_context(context, require_empty=True) == document  # noqa: SLF001
        with pytest.raises(
            e4_v1.ConstructionK7H1E3BoundOutputOrdinalContinuationV1Error,
            match="caller-minted",
        ):
            e4_v1.H1E3BoundOutputContinuationContextV1(
                object(),
                context.payload_bytes,
                context._owner_key,  # noqa: SLF001
                context._parent_fd,  # noqa: SLF001
                context._directory_fd,  # noqa: SLF001
                context._parent_path,  # noqa: SLF001
                context._directory_path,  # noqa: SLF001
                context._directory_basename,  # noqa: SLF001
            )
    finally:
        e4_v1.close_unconsumed_h1_e3_bound_output_context_v1(context)


def test_prepare_fsyncs_the_pinned_parent_after_child_mkdir(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_fsync = e4_v1.os.fsync
    fsynced_directories: list[tuple[int, int]] = []

    def record_fsync(descriptor: int) -> None:
        metadata = os.fstat(descriptor)
        if os.path.isdir(f"/proc/self/fd/{descriptor}"):
            fsynced_directories.append((metadata.st_dev, metadata.st_ino))
        original_fsync(descriptor)

    monkeypatch.setattr(e4_v1.os, "fsync", record_fsync)
    context = _prepare(tmp_path)
    try:
        recorded = context.to_document()["output_directory"]
        assert (recorded["parent_device"], recorded["parent_inode"]) in (
            fsynced_directories
        )
    finally:
        e4_v1.close_unconsumed_h1_e3_bound_output_context_v1(context)


def test_joint_fixed_point_is_exact_deterministic_and_has_two_terminal_replays(
    tmp_path: Path,
) -> None:
    context = _prepare(tmp_path)
    try:
        first = e4_v1.solve_h1_e3_bound_output_joint_fixed_point_for_construction_v1(
            context=context,
            upstream_completion_id=_id("pure-upstream"),
            upstream_session_nonce=_id("pure-session"),
        )
        second = e4_v1.solve_h1_e3_bound_output_joint_fixed_point_for_construction_v1(
            context=context,
            upstream_completion_id=_id("pure-upstream"),
            upstream_session_nonce=_id("pure-session"),
        )
        assert first.fixed_point_id == second.fixed_point_id
        assert first.role_bytes == second.role_bytes
        document = first.to_document()
        assert document["e3_completion_verified"] is False
        assert document["exact_componentwise_fixed_point"] is True
        assert document["terminal_replay_count"] == 2
        assert document["terminal_replays_identical"] is True
        assert document["maximum_simultaneous_render_sets"] == 2
        assert document["two_render_live_set_bound_verified"] is True
        assert document["fixed_output_bytes"] == sum(
            len(raw) for _role, raw in first.role_bytes
        )
        assert document["fixed_output_read_bytes"] == 17 + document["fixed_output_bytes"]
        assert len(document["iterations"]) <= 32
        assert document["iterations"][-1]["converged"] is True
        assert all(
            len(raw) <= e4_v1.MAX_ROLE_BYTES for _role, raw in first.role_bytes
        )
        manifest = dict(first.role_bytes)["OUTPUT_MANIFEST"]
        manifest_document = e4_v1.loads_canonical_json(manifest)
        assert [row["role"] for row in manifest_document["ordered_nonmanifest_roles"]] == list(
            e4_v1.ROLE_ORDER[:-1]
        )
        assert manifest_document["manifest_self_identity_present"] is False
        assert manifest_document["manifest_self_hash_present"] is False
        assert manifest_document["manifest_self_extent_present"] is False
    finally:
        e4_v1.close_unconsumed_h1_e3_bound_output_context_v1(context)


def test_public_gate_rejects_typed_null_posthoc_v8_e2_crash_and_unavailable(
    tmp_path: Path,
) -> None:
    context = _prepare(tmp_path)
    try:
        foreign_inputs = (
            {
                "schema": "acfqp.k7_h1_exclusive_broker_completion.v1",
                "authority_disposition": "BROKER_EXCLUSIVE_PRESENT",
                "prebound_output_continuation_context_id": {
                    "kind": "NOT_APPLICABLE",
                    "reason": "OUTPUT_CONTINUATION_NOT_PREBOUND",
                },
            },
            {"authority_disposition": "PRESENT_LIVE", "source": "V8"},
            {"authority_disposition": "CLEANUP_ACTION_DRAINED", "source": "E2"},
            e3_v1.run_h1_exclusive_native_resource_broker_v1(
                source_payloads={
                    site: canonical_json_bytes({"site": site})
                    for site in e3_v1.SOURCE_SITE_ORDER
                },
            ),
        )
        assert type(foreign_inputs[-1]) is e3_v1.H1ExclusiveBrokerUnavailableV1
        for foreign in foreign_inputs:
            with pytest.raises(
                e4_v1.ConstructionK7H1E3BoundOutputOrdinalContinuationV1Error,
                match="only exact issuer-owned E3 completion",
            ):
                e4_v1.continue_h1_e3_bound_output_ordinals_v1(
                    context=context,
                    e3_completion=foreign,  # type: ignore[arg-type]
                )
        assert os.listdir(context._directory_fd) == []  # noqa: SLF001
        assert id(context) in e4_v1._LIVE_CONTEXTS  # noqa: SLF001
        assert "guardian" not in inspect.signature(
            e4_v1.continue_h1_e3_bound_output_ordinals_v1
        ).parameters
        assert e1_v1.H1NativeCapabilityGuardianV1 is not e3_v1.H1ExclusiveBrokerCompletionV1
        assert e2_v1.H1CleanupActionJournalHandleV1 is not e3_v1.H1ExclusiveBrokerCompletionV1
    finally:
        e4_v1.close_unconsumed_h1_e3_bound_output_context_v1(context)


def test_cross_directory_replacement_is_rejected_before_writer_allocation(
    tmp_path: Path,
) -> None:
    context = _prepare(tmp_path)
    original = context._directory_path  # noqa: SLF001
    moved = tmp_path / "moved-original"
    original.rename(moved)
    original.mkdir(mode=0o700)
    try:
        with pytest.raises(
            e4_v1.ConstructionK7H1E3BoundOutputOrdinalContinuationV1Error,
            match="crossed its pinned",
        ):
            e4_v1._verify_live_context(context, require_empty=True)  # noqa: SLF001
    finally:
        e4_v1._retire_context(context)  # noqa: SLF001
        original.rmdir()
        moved.rmdir()


def test_context_copy_thread_fork_and_reentry_cannot_create_second_writer(
    tmp_path: Path,
) -> None:
    context = _prepare(tmp_path)
    with pytest.raises(
        e4_v1.ConstructionK7H1E3BoundOutputOrdinalContinuationV1Error,
        match="cannot be copied",
    ):
        copy.copy(context)
    with pytest.raises(
        e4_v1.ConstructionK7H1E3BoundOutputOrdinalContinuationV1Error,
        match="deep-copied",
    ):
        copy.deepcopy(context)
    thread_errors: list[BaseException] = []

    def cross_thread() -> None:
        try:
            e4_v1._verify_live_context(context, require_empty=True)  # noqa: SLF001
        except BaseException as error:
            thread_errors.append(error)

    worker = threading.Thread(target=cross_thread)
    worker.start()
    worker.join()
    assert len(thread_errors) == 1
    assert isinstance(
        thread_errors[0],
        e4_v1.ConstructionK7H1E3BoundOutputOrdinalContinuationV1Error,
    )
    read_end, write_end = os.pipe()
    child = os.fork()
    if child == 0:  # pragma: no cover - asserted by parent pipe
        os.close(read_end)
        rejected = False
        fd_closed = False
        try:
            e4_v1._verify_live_context(context, require_empty=True)  # noqa: SLF001
        except e4_v1.ConstructionK7H1E3BoundOutputOrdinalContinuationV1Error:
            rejected = True
        try:
            os.fstat(context._directory_fd)  # noqa: SLF001
        except OSError as error:
            fd_closed = error.errno == errno.EBADF
        try:
            os.fstat(context._parent_fd)  # noqa: SLF001
        except OSError as error:
            fd_closed = fd_closed and error.errno == errno.EBADF
        os.write(write_end, b"OK" if rejected and fd_closed else b"BAD")
        os.close(write_end)
        os._exit(0)
    os.close(write_end)
    observed = os.read(read_end, 3)
    os.close(read_end)
    _pid, status = os.waitpid(child, 0)
    assert observed == b"OK"
    assert os.waitstatus_to_exitcode(status) == 0
    assert e4_v1._verify_live_context(context, require_empty=True)  # noqa: SLF001
    context_document = context.to_document()
    result = e4_v1._run_admitted_output_program(  # noqa: SLF001
        context=context,
        context_document=context_document,
        e3_completion=_synthetic_admitted_completion(),
        fault=e4_v1.H1E4FaultInjectionV1.NONE,
    )
    assert type(result) is e4_v1.H1E3BoundOutputCompletionV1
    with pytest.raises(
        e4_v1.ConstructionK7H1E3BoundOutputOrdinalContinuationV1Error,
        match="exact live retained",
    ):
        e4_v1._verify_live_context(context, require_empty=False)  # noqa: SLF001


def test_close_that_raises_after_definitive_kernel_close_does_not_lose_registry(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = _prepare(tmp_path)
    context_document = context.to_document()
    original_close = e4_v1.os.close
    injected = False

    def close_then_raise(descriptor: int) -> None:
        nonlocal injected
        if descriptor == context._directory_fd and not injected:  # noqa: SLF001
            injected = True
            original_close(descriptor)
            raise OSError(errno.EINTR, "injected post-close error")
        original_close(descriptor)

    monkeypatch.setattr(e4_v1.os, "close", close_then_raise)
    result = e4_v1._run_admitted_output_program(  # noqa: SLF001
        context=context,
        context_document=context_document,
        e3_completion=_synthetic_admitted_completion(),
        fault=e4_v1.H1E4FaultInjectionV1.NONE,
    )
    assert injected is True
    assert type(result) is e4_v1.H1E3BoundOutputCompletionV1
    assert id(context) not in e4_v1._LIVE_CONTEXTS  # noqa: SLF001
    assert id(context) in e4_v1._CONSUMED_CONTEXTS  # noqa: SLF001


def test_persistent_live_close_failure_is_quarantined_and_retryable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = _prepare(tmp_path)
    context_document = context.to_document()
    original_close = e4_v1.os.close
    blocked_fd: int | None = None

    def leave_one_role_live(descriptor: int) -> None:
        nonlocal blocked_fd
        rows = e4_v1._owned_fd_rows(context._owner_key)  # noqa: SLF001
        label = rows.get(descriptor, {}).get("label")
        if label == "ROLE:BUSINESS_RESULT":
            blocked_fd = descriptor
            raise OSError(errno.EIO, "injected still-live close failure")
        original_close(descriptor)

    monkeypatch.setattr(e4_v1.os, "close", leave_one_role_live)
    result = e4_v1._run_admitted_output_program(  # noqa: SLF001
        context=context,
        context_document=context_document,
        e3_completion=_synthetic_admitted_completion(),
        fault=e4_v1.H1E4FaultInjectionV1.NONE,
    )
    assert type(result) is e4_v1.H1E3BoundOutputPartialNoncertificateV1
    document = result.to_document()
    assert blocked_fd is not None
    assert document["writer_handles_closed_without_success_ordinal"] is False
    assert document["context_consumed"] is False
    assert document["cleanup_quarantine_present"] is True
    assert document["outstanding_owned_fd_labels"] == ["ROLE:BUSINESS_RESULT"]
    assert id(context) in e4_v1._QUARANTINED_CONTEXTS  # noqa: SLF001
    assert id(context) not in e4_v1._CONSUMED_CONTEXTS  # noqa: SLF001
    assert os.fstat(blocked_fd)
    monkeypatch.setattr(e4_v1.os, "close", original_close)
    e4_v1.retry_h1_e3_bound_output_fd_quarantine_v1(context)
    assert id(context) not in e4_v1._QUARANTINED_CONTEXTS  # noqa: SLF001
    assert id(context) in e4_v1._CONSUMED_CONTEXTS  # noqa: SLF001
    with pytest.raises(OSError) as closed:
        os.fstat(blocked_fd)
    assert closed.value.errno == errno.EBADF


def test_fork_during_role_commit_closes_all_child_writer_fds(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = _prepare(tmp_path)
    context_document = context.to_document()
    original_write_all = e4_v1._write_all  # noqa: SLF001
    exercised = False

    def write_with_fork(descriptor: int, raw: bytes) -> None:
        nonlocal exercised
        if not exercised:
            exercised = True
            read_end, write_end = os.pipe()
            child = os.fork()
            if child == 0:  # pragma: no cover - asserted by parent pipe
                os.close(read_end)
                inherited = (
                    context._parent_fd,  # noqa: SLF001
                    context._directory_fd,  # noqa: SLF001
                    descriptor,
                )
                closed = True
                for candidate in inherited:
                    try:
                        os.fstat(candidate)
                    except OSError as error:
                        closed = closed and error.errno == errno.EBADF
                    else:
                        closed = False
                os.write(write_end, b"OK" if closed else b"BAD")
                os.close(write_end)
                os._exit(0)
            os.close(write_end)
            observed = os.read(read_end, 3)
            os.close(read_end)
            _pid, status = os.waitpid(child, 0)
            assert observed == b"OK"
            assert os.waitstatus_to_exitcode(status) == 0
        original_write_all(descriptor, raw)

    monkeypatch.setattr(e4_v1, "_write_all", write_with_fork)
    result = e4_v1._run_admitted_output_program(  # noqa: SLF001
        context=context,
        context_document=context_document,
        e3_completion=_synthetic_admitted_completion(),
        fault=e4_v1.H1E4FaultInjectionV1.NONE,
    )
    assert exercised is True
    assert type(result) is e4_v1.H1E3BoundOutputCompletionV1


def test_fixed_point_never_retains_more_than_two_render_sets(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = _prepare(tmp_path)
    original_render = e4_v1._render_role_set  # noqa: SLF001

    class TrackedTuple(tuple):
        live = 0
        maximum = 0

        def __new__(cls, rows: tuple[tuple[str, bytes], ...]) -> "TrackedTuple":
            instance = super().__new__(cls, rows)
            cls.live += 1
            cls.maximum = max(cls.maximum, cls.live)
            return instance

        def __del__(self) -> None:
            type(self).live -= 1

    def tracked_render(**kwargs: object) -> TrackedTuple:
        return TrackedTuple(original_render(**kwargs))

    monkeypatch.setattr(e4_v1, "_render_role_set", tracked_render)
    fixed = e4_v1.solve_h1_e3_bound_output_joint_fixed_point_for_construction_v1(
        context=context,
        upstream_completion_id=_id("tracked-upstream"),
        upstream_session_nonce=_id("tracked-session"),
    )
    assert fixed.to_document()["maximum_simultaneous_render_sets"] == 2
    assert TrackedTuple.maximum == 2
    del fixed
    gc.collect()
    assert TrackedTuple.live == 0
    e4_v1.close_unconsumed_h1_e3_bound_output_context_v1(context)


def test_internal_admitted_program_persists_exact_eight_files_and_53_to_62(
    tmp_path: Path,
) -> None:
    context, result = _run_internal_success(tmp_path)
    document = result.to_document()
    assert e4_v1.verify_h1_e3_bound_output_completion_structure_v1(result)
    assert document["completed_output_ordinals"] == list(range(53, 63))
    assert [row["role"] for row in document["durable_role_commits"]] == list(
        e4_v1.ROLE_ORDER
    )
    assert [
        row["normal_ordinal"] for row in document["output_ordinal_events_53_to_60"]
    ] == list(range(53, 61))
    assert document["ordinal_61_finalization"]["normal_ordinal"] == 61
    assert document["ordinal_62_writer_close"]["normal_ordinal"] == 62
    assert document["ordinal_62_writer_close"]["context_consumed"] is True
    assert document["route_wide_peak_authority_present"] is False
    assert document["peak_scope_status"] == "PEAK_SCOPE_UNRESOLVED"
    assert sorted(path.name for path in context._directory_path.iterdir()) == sorted(  # noqa: SLF001
        e4_v1.ROLE_FILE_NAMES.values()
    )
    assert e4_v1.verify_persisted_h1_e3_bound_output_files_for_evaluation_v1(
        completion=result,
        output_directory=context._directory_path,  # noqa: SLF001
    )
    with pytest.raises(
        e4_v1.ConstructionK7H1E3BoundOutputOrdinalContinuationV1Error,
        match="exact live retained",
    ):
        e4_v1._verify_live_context(context, require_empty=False)  # noqa: SLF001


@pytest.mark.parametrize(
    "fault",
    tuple(fault for fault in e4_v1.H1E4FaultInjectionV1 if fault.value != "NONE"),
)
def test_every_filesystem_sequence_and_crash_injection_is_partial_noncertificate(
    tmp_path: Path,
    fault: e4_v1.H1E4FaultInjectionV1,
) -> None:
    context = _prepare(tmp_path)
    context_document = e4_v1._verify_live_context(  # noqa: SLF001
        context, require_empty=True
    )
    result = e4_v1._run_admitted_output_program(  # noqa: SLF001
        context=context,
        context_document=context_document,
        e3_completion=_synthetic_admitted_completion(),
        fault=fault,
    )
    assert type(result) is e4_v1.H1E3BoundOutputPartialNoncertificateV1
    document = result.to_document()
    assert document["terminal_class"] == "ATTEMPT_CLOSURE_NONCERTIFICATE"
    assert document["terminal_code"] == "PROTOCOL_FAILURE"
    assert document["fault_injection"] == fault.value
    assert document["output_ordinals_53_to_62_success_events_issued"] is False
    assert document["construction_output_completion_present"] is False
    assert document["ordinal_62_writer_close"] is None
    assert document["writer_handles_closed_without_success_ordinal"] is True
    assert document["context_consumed"] is True
    assert document["official_execution_allowed"] is False
    assert context.context_id in e4_v1._CONSUMED_CONTEXT_IDS  # noqa: SLF001


def test_completion_tamper_reorder_duplicate_and_peak_relabel_are_rejected(
    tmp_path: Path,
) -> None:
    _context, result = _run_internal_success(tmp_path)
    original = result.to_document()
    attacks = []
    reordered = {**original}
    reordered["output_ordinal_events_53_to_60"] = list(
        original["output_ordinal_events_53_to_60"]
    )
    reordered["output_ordinal_events_53_to_60"][0], reordered[
        "output_ordinal_events_53_to_60"
    ][1] = (
        reordered["output_ordinal_events_53_to_60"][1],
        reordered["output_ordinal_events_53_to_60"][0],
    )
    attacks.append(reordered)
    duplicated = {**original}
    duplicated["output_ordinal_events_53_to_60"] = list(
        original["output_ordinal_events_53_to_60"]
    ) + [original["output_ordinal_events_53_to_60"][0]]
    attacks.append(duplicated)
    peak = {**original, "route_wide_peak_authority_present": True}
    attacks.append(peak)
    for attack in attacks:
        with pytest.raises(
            e4_v1.ConstructionK7H1E3BoundOutputOrdinalContinuationV1Error
        ):
            e4_v1.verify_h1_e3_bound_output_completion_structure_v1(attack)


def test_coherently_resigned_role_and_fixed_point_pass_structure_but_fail_rederivation(
    tmp_path: Path,
) -> None:
    context, result = _run_internal_success(tmp_path)
    attack = copy.deepcopy(result.to_document())

    def resign(row: dict[str, object], domain: str, id_field: str) -> None:
        row.pop(id_field, None)
        row[id_field] = e4_v1._domain_id(domain, row)  # noqa: SLF001

    # Same-width semantic corruption keeps the O/R recurrence numerically
    # unchanged, then every affected nested content object is re-signed.
    work_index = e4_v1.ROLE_ORDER.index("WORK_VECTOR")
    work_document = attack["durable_role_documents"][work_index]
    work_document["witness_semantics"]["kind"] = "WORK_VECTOX"
    changed = {
        "role": "WORK_VECTOR",
        "normal_ordinal": 57,
        "file_name": e4_v1.ROLE_FILE_NAMES["WORK_VECTOR"],
        "construction_role_witness_id": e4_v1._domain_id(  # noqa: SLF001
            domains_v11.CONSTRUCTION_K7_H1_E3_BOUND_OUTPUT_ROLE_WITNESS_V1_DOMAIN,
            work_document,
        ),
        "sha256": e4_v1._sha(canonical_json_bytes(work_document)),  # noqa: SLF001
        "byte_count": len(canonical_json_bytes(work_document)),
    }
    manifest_document = attack["durable_role_documents"][-1]
    manifest_document["ordered_nonmanifest_roles"][work_index] = dict(changed)
    manifest_changed = {
        "role": "OUTPUT_MANIFEST",
        "normal_ordinal": 60,
        "file_name": e4_v1.ROLE_FILE_NAMES["OUTPUT_MANIFEST"],
        "construction_role_witness_id": e4_v1._domain_id(  # noqa: SLF001
            domains_v11.CONSTRUCTION_K7_H1_E3_BOUND_OUTPUT_ROLE_WITNESS_V1_DOMAIN,
            manifest_document,
        ),
        "sha256": e4_v1._sha(canonical_json_bytes(manifest_document)),  # noqa: SLF001
        "byte_count": len(canonical_json_bytes(manifest_document)),
    }
    fixed = attack["joint_fixed_point"]
    fixed["role_artifacts"][work_index] = dict(changed)
    fixed["role_artifacts"][-1] = dict(manifest_changed)
    fixed["terminal_role_set_sha256"] = e4_v1._sha(  # noqa: SLF001
        canonical_json_bytes(
            [
                {"role": row["role"], "sha256": row["sha256"]}
                for row in fixed["role_artifacts"]
            ]
        )
    )
    resign(
        fixed,
        domains_v11.CONSTRUCTION_K7_H1_JOINT_OUTPUT_READ_FIXED_POINT_V1_DOMAIN,
        "h1_joint_output_read_fixed_point_id",
    )
    fixed_id = fixed["h1_joint_output_read_fixed_point_id"]
    for index, (commit, event) in enumerate(
        zip(
            attack["durable_role_commits"],
            attack["output_ordinal_events_53_to_60"],
        )
    ):
        metadata = changed if index == work_index else (
            manifest_changed if index == len(e4_v1.ROLE_ORDER) - 1 else None
        )
        if metadata is not None:
            commit["construction_role_witness_id"] = metadata[
                "construction_role_witness_id"
            ]
            commit["sha256"] = metadata["sha256"]
            commit["byte_count"] = metadata["byte_count"]
            event["sha256"] = metadata["sha256"]
            event["byte_count"] = metadata["byte_count"]
        commit["h1_joint_output_read_fixed_point_id"] = fixed_id
        event["h1_joint_output_read_fixed_point_id"] = fixed_id
        resign(
            commit,
            domains_v11.CONSTRUCTION_K7_H1_E3_BOUND_OUTPUT_ROLE_COMMIT_V1_DOMAIN,
            "h1_e3_bound_output_role_commit_id",
        )
        resign(
            event,
            domains_v11.CONSTRUCTION_K7_H1_E3_BOUND_OUTPUT_ORDINAL_EVENT_V1_DOMAIN,
            "h1_e3_bound_output_ordinal_event_id",
        )
    finalization = attack["ordinal_61_finalization"]
    finalization["h1_joint_output_read_fixed_point_id"] = fixed_id
    finalization["role_commit_ids"] = [
        row["h1_e3_bound_output_role_commit_id"]
        for row in attack["durable_role_commits"]
    ]
    finalization["ordinal_53_to_60_event_ids"] = [
        row["h1_e3_bound_output_ordinal_event_id"]
        for row in attack["output_ordinal_events_53_to_60"]
    ]
    resign(
        finalization,
        domains_v11.CONSTRUCTION_K7_H1_E3_BOUND_OUTPUT_FINALIZATION_V1_DOMAIN,
        "h1_e3_bound_output_finalization_id",
    )
    close_event = attack["ordinal_62_writer_close"]
    close_event["h1_e3_bound_output_finalization_id"] = finalization[
        "h1_e3_bound_output_finalization_id"
    ]
    resign(
        close_event,
        domains_v11.CONSTRUCTION_K7_H1_E3_BOUND_OUTPUT_WRITER_CLOSE_V1_DOMAIN,
        "h1_e3_bound_output_writer_close_id",
    )
    resign(
        attack,
        domains_v11.CONSTRUCTION_K7_H1_E3_BOUND_OUTPUT_COMPLETION_V1_DOMAIN,
        "h1_e3_bound_output_completion_id",
    )
    assert e4_v1.verify_h1_e3_bound_output_completion_structure_v1(attack)
    with pytest.raises(
        e4_v1.ConstructionK7H1E3BoundOutputOrdinalContinuationV1Error,
        match="differs from full reconstructed completion",
    ):
        e4_v1._verify_rederived_completion_semantics(  # noqa: SLF001
            completion_document=attack,
            context_document=context.to_document(),
            exact_e3_completion_document=_synthetic_admitted_completion(),
        )


def test_coherently_resigned_commit_flag_fails_full_authoritative_reconstruction(
    tmp_path: Path,
) -> None:
    context, result = _run_internal_success(tmp_path)
    attack = copy.deepcopy(result.to_document())

    def resign(row: dict[str, object], domain: str, id_field: str) -> None:
        row.pop(id_field, None)
        row[id_field] = e4_v1._domain_id(domain, row)  # noqa: SLF001

    attack["durable_role_commits"][0]["construction_witness_only"] = False
    resign(
        attack["durable_role_commits"][0],
        domains_v11.CONSTRUCTION_K7_H1_E3_BOUND_OUTPUT_ROLE_COMMIT_V1_DOMAIN,
        "h1_e3_bound_output_role_commit_id",
    )
    finalization = attack["ordinal_61_finalization"]
    finalization["role_commit_ids"] = [
        row["h1_e3_bound_output_role_commit_id"]
        for row in attack["durable_role_commits"]
    ]
    resign(
        finalization,
        domains_v11.CONSTRUCTION_K7_H1_E3_BOUND_OUTPUT_FINALIZATION_V1_DOMAIN,
        "h1_e3_bound_output_finalization_id",
    )
    close_event = attack["ordinal_62_writer_close"]
    close_event["h1_e3_bound_output_finalization_id"] = finalization[
        "h1_e3_bound_output_finalization_id"
    ]
    resign(
        close_event,
        domains_v11.CONSTRUCTION_K7_H1_E3_BOUND_OUTPUT_WRITER_CLOSE_V1_DOMAIN,
        "h1_e3_bound_output_writer_close_id",
    )
    resign(
        attack,
        domains_v11.CONSTRUCTION_K7_H1_E3_BOUND_OUTPUT_COMPLETION_V1_DOMAIN,
        "h1_e3_bound_output_completion_id",
    )
    assert e4_v1.verify_h1_e3_bound_output_completion_structure_v1(attack)
    with pytest.raises(
        e4_v1.ConstructionK7H1E3BoundOutputOrdinalContinuationV1Error,
        match="differs from full reconstructed completion",
    ):
        e4_v1._verify_rederived_completion_semantics(  # noqa: SLF001
            completion_document=attack,
            context_document=context.to_document(),
            exact_e3_completion_document=_synthetic_admitted_completion(),
        )


def test_all_witness_roles_are_rejected_by_formal_parsers(tmp_path: Path) -> None:
    _context, result = _run_internal_success(tmp_path)
    roles = {
        row["role"]: row for row in result.to_document()["durable_role_documents"]
    }
    with pytest.raises(accounting_v1.AccountingV1Error):
        accounting_v1.CounterRecordV1.from_dict(roles["COUNTER_RECORD_SET"])
    with pytest.raises(accounting_v1.AccountingV1Error):
        accounting_v1.WorkVectorV1.from_dict(
            roles["WORK_VECTOR"], accounting_v1.official_counter_registry_v1()
        )
    with pytest.raises(accounting_v1.AccountingV1Error):
        accounting_v1.ComparisonVectorV1.from_dict(roles["COMPARISON_VECTOR"])
    with pytest.raises(actual_accounting_v1.ActualAccountingV1Error):
        actual_accounting_v1.ActualProjectionProofV1.from_dict(
            roles["ACTUAL_PROJECTION_PROOF"]
        )
    with pytest.raises(routing_v1.RoutingV1Error):
        routing_v1.TerminalArtifactV1.from_dict(roles["TERMINAL_ARTIFACT"])


def _e3_sources() -> dict[str, bytes]:
    return {
        site: canonical_json_bytes(
            {"schema": "acfqp.test.e4.real_e3_source.v1", "site_key": site}
        )
        for site in e3_v1.SOURCE_SITE_ORDER
    }


@pytest.mark.skipif(
    not (
        os.environ.get("ACFQP_E3_WORKER_CGROUP")
        and os.environ.get("ACFQP_E3_BUSINESS_CGROUP")
    ),
    reason="two preconfigured delegated E3 cgroup-v2 leaves were not registered",
)
def test_real_e3_prebinding_continues_to_exact_e4_success(tmp_path: Path) -> None:
    context = _prepare(tmp_path)
    worker_fd = os.open(
        os.environ["ACFQP_E3_WORKER_CGROUP"],
        os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC,
    )
    business_fd = os.open(
        os.environ["ACFQP_E3_BUSINESS_CGROUP"],
        os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC,
    )
    try:
        e3_result = e3_v1.run_h1_exclusive_native_resource_broker_v1(
            source_payloads=_e3_sources(),
            worker_cgroup_fd=worker_fd,
            business_cgroup_fd=business_fd,
            prebound_output_continuation_context_id=context.context_id,
            deadline_milliseconds=60_000,
        )
    finally:
        os.close(worker_fd)
        os.close(business_fd)
    assert type(e3_result) is e3_v1.H1ExclusiveBrokerCompletionV1
    result = e4_v1.continue_h1_e3_bound_output_ordinals_v1(
        context=context,
        e3_completion=e3_result,
    )
    assert type(result) is e4_v1.H1E3BoundOutputCompletionV1
    assert e4_v1.verify_h1_e3_bound_output_completion_v1(
        completion=result,
        context=context,
        e3_completion=e3_result,
    )
