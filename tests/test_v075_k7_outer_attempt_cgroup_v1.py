from __future__ import annotations

import inspect
import os
import pickle

import pytest

from acfqp import v075_k7_os_supervisor_admission_v1 as admission_v1
from acfqp import v075_k7_outer_attempt_cgroup_v1 as outer_v1
from acfqp.phase3e_ids import PHASE3E_DOMAIN_TAGS, canonical_json_bytes
from tests.test_v075_k7_atomic_pidfd_runtime_v1 import _successor_request
from tests.test_v075_k7_parent_atomic_executor_v1 import (
    _delegated_scope_parent_fd,
)


def _issue(request, admission_result, descriptor):
    return outer_v1.official_v075_k7_outer_attempt_cgroup_nonce_service_v1().issue(
        request=request,
        admission_result=admission_result,
        delegated_parent_fd=descriptor,
    )


def test_profile_freezes_outer_hierarchy_without_premature_formal_claim() -> None:
    assert outer_v1.PROPOSED_CONTRACT_VERSION == "2.0.3"
    assert outer_v1.LOCAL_DOMAIN_TAGS <= PHASE3E_DOMAIN_TAGS
    document = (
        outer_v1.official_v075_k7_outer_attempt_cgroup_profile_v1().to_document()
    )
    assert document["topology"] == (
        "EMPTY_ANCESTOR_WITH_WORKER_AND_FUTURE_BUSINESS_SIBLING"
    )
    assert document["readiness_level"] == "PREP_ONLY"
    assert document["normal_future_process_launch_count"] == 2
    assert document["pids_max_is_cumulative_launch_count"] is False
    assert document["memory_connection_status"] == "OUTER_HIERARCHY_PREP_ONLY"
    assert document["process_connection_status"] == (
        "EXTERNAL_BROKER_NOT_IMPLEMENTED"
    )
    assert all(value is False for value in outer_v1._locks().values())  # noqa: SLF001
    assert document["exclusive_parent_writer_verified"] is False
    assert document["atomic_name_to_inode_delete_verified"] is False
    assert document["guardian_cleanup_authority_bound"] is False
    assert document["safe_for_exact_runtime_consumption"] is False
    assert document["post_identity_setup_cleanup_retryable"] is True
    assert document["pre_identity_create_cleanup_requires_parent_guard"] is True
    assert "nonce_token" in inspect.signature(
        outer_v1.acquire_v075_k7_outer_attempt_cgroup_v1
    ).parameters
    assert canonical_json_bytes(document)


def test_temp_directory_is_typed_blocker_without_mutation(tmp_path) -> None:
    request = _successor_request("outer-not-cgroup2")
    descriptor = os.open(tmp_path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        admission_result = admission_v1.probe_v075_k7_os_supervisor_admission_v1(
            delegated_parent_fd=descriptor
        )
        token = _issue(request, admission_result, descriptor)
        before = tuple(tmp_path.iterdir())
        blocked = outer_v1.acquire_v075_k7_outer_attempt_cgroup_v1(
            request=request,
            admission_result=admission_result,
            delegated_parent_fd=descriptor,
            nonce_token=token,
        )
        after = tuple(tmp_path.iterdir())
    finally:
        os.close(descriptor)
    assert type(blocked) is outer_v1.K7OuterAttemptCgroupBlockedResultV1
    assert blocked.blocker is outer_v1.K7OuterAttemptCgroupBlockerV1.NOT_CGROUP2_FILESYSTEM
    assert before == after == ()
    document = blocked.to_document()
    assert document["cleanup_complete"] is True
    assert document["worker_launch_attempted"] is False
    assert document["memory_value_present"] is False
    assert document["memory_evidence_issued"] is False
    assert document["counter_records_issued"] is False


def test_nonce_is_consumed_before_filesystem_probe(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    request = _successor_request("outer-single-use")
    descriptor = os.open(tmp_path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        admission_result = admission_v1.probe_v075_k7_os_supervisor_admission_v1(
            delegated_parent_fd=descriptor
        )
        token = _issue(request, admission_result, descriptor)
        calls = 0

        def fake_magic(_descriptor):
            nonlocal calls
            calls += 1
            return -1

        monkeypatch.setattr(outer_v1.inner_v1, "_fstatfs_magic", fake_magic)
        first = outer_v1.acquire_v075_k7_outer_attempt_cgroup_v1(
            request=request,
            admission_result=admission_result,
            delegated_parent_fd=descriptor,
            nonce_token=token,
        )
        assert type(first) is outer_v1.K7OuterAttemptCgroupBlockedResultV1
        assert calls == 1
        with pytest.raises(
            outer_v1.V075K7OuterAttemptCgroupV1Error,
            match="already consumed",
        ):
            outer_v1.acquire_v075_k7_outer_attempt_cgroup_v1(
                request=request,
                admission_result=admission_result,
                delegated_parent_fd=descriptor,
                nonce_token=token,
            )
        assert calls == 1
    finally:
        os.close(descriptor)


def test_post_create_validation_failure_removes_owned_outer_directory(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    request = _successor_request("outer-cleanup")
    descriptor = os.open(tmp_path, os.O_RDONLY | os.O_DIRECTORY)
    original_read = outer_v1.inner_v1._read_control  # noqa: SLF001
    try:
        admission_result = admission_v1.probe_v075_k7_os_supervisor_admission_v1(
            delegated_parent_fd=descriptor
        )
        token = _issue(request, admission_result, descriptor)

        def fake_read(directory_fd, name):
            if name in {"cgroup.controllers", "cgroup.subtree_control"}:
                return b"memory pids\n"
            if name == "cgroup.stat":
                return b"nr_descendants 0\nnr_dying_descendants 0\n"
            return original_read(directory_fd, name)

        monkeypatch.setattr(
            outer_v1.inner_v1,
            "_fstatfs_magic",
            lambda _descriptor: outer_v1.inner_v1.CGROUP2_SUPER_MAGIC,
        )
        monkeypatch.setattr(outer_v1.inner_v1, "_read_control", fake_read)
        blocked = outer_v1.acquire_v075_k7_outer_attempt_cgroup_v1(
            request=request,
            admission_result=admission_result,
            delegated_parent_fd=descriptor,
            nonce_token=token,
        )
    finally:
        os.close(descriptor)
    assert blocked.blocker is outer_v1.K7OuterAttemptCgroupBlockerV1.OUTER_VALIDATION_FAILED
    assert blocked.outer_created is True
    assert blocked.cleanup_complete is True
    assert tuple(tmp_path.iterdir()) == ()


def test_nonce_and_lease_roles_are_not_caller_mintable(tmp_path) -> None:
    request = _successor_request("outer-mint")
    descriptor = os.open(tmp_path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        admission_result = admission_v1.probe_v075_k7_os_supervisor_admission_v1(
            delegated_parent_fd=descriptor
        )
        token = _issue(request, admission_result, descriptor)
        with pytest.raises(TypeError, match="unpickleable"):
            pickle.dumps(token)
        with pytest.raises(TypeError, match="unpickleable"):
            pickle.dumps(
                outer_v1.official_v075_k7_outer_attempt_cgroup_nonce_service_v1()
            )
        with pytest.raises(
            outer_v1.V075K7OuterAttemptCgroupV1Error,
            match="issuer-owned",
        ):
            outer_v1.K7OuterAttemptCgroupProfileV1(object())
        with pytest.raises(
            outer_v1.V075K7OuterAttemptCgroupV1Error,
            match="issuer-owned",
        ):
            outer_v1.K7OuterAttemptCgroupCleanupGuardV1(
                object(),
                parent_fd=descriptor,
                outer_fd=-1,
                worker_fd=-1,
                outer_name=None,
                worker_name=None,
                parent_status=os.fstat(descriptor),
                outer_status=None,
                worker_status=None,
            )
        with pytest.raises(
            outer_v1.V075K7OuterAttemptCgroupV1Error,
            match="issuer-owned",
        ):
            outer_v1.K7OuterAttemptCgroupBlockedResultV1(
                object(),
                request.request_id,
                request.route_identity.route_identity_id,
                admission_result.result_id,
                outer_v1.K7OuterAttemptCgroupBlockerV1.NOT_CGROUP2_FILESYSTEM,
                outer_v1.K7OuterAttemptCgroupStageV1.FILESYSTEM,
                False,
                False,
                True,
            )
    finally:
        os.close(descriptor)


def test_frozen_caps_have_capacity_for_worker_and_one_inner_child() -> None:
    assert dict(outer_v1.OUTER_CONTROL_READBACKS) == {
        "memory.max": str(4 * 1024 * 1024 * 1024),
        "memory.swap.max": "0",
        "pids.max": "2",
        "cgroup.max.depth": "1",
        "cgroup.max.descendants": "2",
    }
    assert dict(outer_v1.WORKER_CONTROL_READBACKS) == {
        "pids.max": "1",
        "cgroup.max.depth": "0",
        "cgroup.max.descendants": "0",
    }


def test_name_to_inode_swap_is_rejected_without_removing_replacement(
    tmp_path,
) -> None:
    original = tmp_path / "owned"
    moved = tmp_path / "moved"
    original.mkdir()
    parent_fd = os.open(tmp_path, os.O_RDONLY | os.O_DIRECTORY)
    owned_fd = os.open(original, os.O_RDONLY | os.O_DIRECTORY)
    expected = os.fstat(owned_fd)
    guard = outer_v1.K7OuterAttemptCgroupCleanupGuardV1(
        outer_v1._CLEANUP_GUARD_ISSUER,  # noqa: SLF001
        parent_fd=parent_fd,
        outer_fd=owned_fd,
        worker_fd=-1,
        outer_name="owned",
        worker_name=None,
        parent_status=os.fstat(parent_fd),
        outer_status=expected,
        worker_status=None,
    )
    original.rename(moved)
    original.mkdir()
    with pytest.raises(
        outer_v1.V075K7OuterAttemptCgroupCleanupV1Error,
        match="retryable cleanup guard",
    ) as caught:
        guard.retry_cleanup()
    assert caught.value.cleanup_guard is guard
    assert original.is_dir()
    assert moved.is_dir()
    original.rmdir()
    moved.rename(original)
    guard.retry_cleanup()
    assert guard.closed is True
    assert not original.exists()


def test_setup_cleanup_guard_resumes_after_partial_removal(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    outer = tmp_path / "outer"
    worker = outer / "worker"
    worker.mkdir(parents=True)
    parent_fd = os.open(tmp_path, os.O_RDONLY | os.O_DIRECTORY)
    outer_fd = os.open(outer, os.O_RDONLY | os.O_DIRECTORY)
    worker_fd = os.open(worker, os.O_RDONLY | os.O_DIRECTORY)
    guard = outer_v1.K7OuterAttemptCgroupCleanupGuardV1(
        outer_v1._CLEANUP_GUARD_ISSUER,  # noqa: SLF001
        parent_fd=parent_fd,
        outer_fd=outer_fd,
        worker_fd=worker_fd,
        outer_name="outer",
        worker_name="worker",
        parent_status=os.fstat(parent_fd),
        outer_status=os.fstat(outer_fd),
        worker_status=os.fstat(worker_fd),
    )
    original_rmdir = os.rmdir
    failed_once = False

    def fail_outer_once(path, *, dir_fd=None):
        nonlocal failed_once
        if path == "outer" and not failed_once:
            failed_once = True
            raise OSError("injected outer removal failure")
        return original_rmdir(path, dir_fd=dir_fd)

    monkeypatch.setattr(outer_v1.os, "rmdir", fail_outer_once)
    with pytest.raises(
        outer_v1.V075K7OuterAttemptCgroupCleanupV1Error,
        match="retryable cleanup guard",
    ) as caught:
        guard.retry_cleanup()
    assert caught.value.cleanup_guard is guard
    assert guard.cleanup_state is (
        outer_v1.K7OuterAttemptCgroupCleanupStateV1.CLEANUP_PARTIAL
    )
    assert not worker.exists()
    assert outer.exists()
    guard.retry_cleanup()
    assert guard.closed is True
    assert not outer.exists()
    with pytest.raises(
        outer_v1.V075K7OuterAttemptCgroupV1Error,
        match="is closed",
    ):
        guard.retry_cleanup()


def test_pre_identity_setup_gap_requires_external_parent_guard(tmp_path) -> None:
    outer = tmp_path / "unbound"
    outer.mkdir()
    parent_fd = os.open(tmp_path, os.O_RDONLY | os.O_DIRECTORY)
    guard = outer_v1.K7OuterAttemptCgroupCleanupGuardV1(
        outer_v1._CLEANUP_GUARD_ISSUER,  # noqa: SLF001
        parent_fd=parent_fd,
        outer_fd=-1,
        worker_fd=-1,
        outer_name="unbound",
        worker_name=None,
        parent_status=os.fstat(parent_fd),
        outer_status=None,
        worker_status=None,
    )
    with pytest.raises(
        outer_v1.V075K7OuterAttemptCgroupCleanupV1Error,
        match="requires an external parent guardian",
    ) as caught:
        guard.retry_cleanup()
    assert caught.value.cleanup_guard is guard
    state = outer_v1.K7OuterAttemptCgroupCleanupStateV1
    assert guard.cleanup_state is state.IDENTITY_UNBOUND_REQUIRES_PARENT_GUARD
    os.rmdir("unbound", dir_fd=parent_fd)
    os.close(parent_fd)


@pytest.mark.skipif(
    os.environ.get("ACFQP_RUN_REAL_CGROUP_INTEGRATION") != "1",
    reason="requires an externally prepared delegated systemd user scope",
)
def test_real_delegated_scope_creates_and_closes_unused_outer_hierarchy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = _successor_request("outer-real")
    with _delegated_scope_parent_fd() as parent_fd:
        admission_result = admission_v1.probe_v075_k7_os_supervisor_admission_v1(
            delegated_parent_fd=parent_fd
        )
        token = _issue(request, admission_result, parent_fd)
        acquired = outer_v1.acquire_v075_k7_outer_attempt_cgroup_v1(
            request=request,
            admission_result=admission_result,
            delegated_parent_fd=parent_fd,
            nonce_token=token,
        )
        assert type(acquired) is outer_v1.K7OuterAttemptCgroupLeaseV1
        document = acquired.to_document()
        assert document["pre_descendant_creation_memory_peak_zero_verified"] is True
        assert document["launch_baseline_memory_peak_value"] is None
        assert document["launch_baseline_reset_required"] is True
        assert document["launch_baseline_memory_peak_reset_verified"] is False
        assert document["cgroup_kill_openability_verified"] is True
        assert document["complete_hierarchy_final_snapshot_verified"] is True
        assert document["controllers_enabled_before_worker_launch"] is True
        assert acquired.outer_fd >= 0
        assert acquired.worker_fd >= 0
        original_wait = outer_v1._wait_descendant_counts  # noqa: SLF001
        failed_once = False

        def fail_once(directory_fd, *, expected_descendants):
            nonlocal failed_once
            if not failed_once:
                failed_once = True
                raise outer_v1.V075K7OuterAttemptCgroupCleanupV1Error(
                    "injected transient descendant drain failure"
                )
            return original_wait(
                directory_fd, expected_descendants=expected_descendants
            )

        def stale_request(_self):
            raise RuntimeError("injected stale request authority")

        with monkeypatch.context() as cleanup_patch:
            cleanup_patch.setattr(
                outer_v1, "_wait_descendant_counts", fail_once
            )
            cleanup_patch.setattr(type(request), "_assert_current", stale_request)
            with pytest.raises(
                outer_v1.V075K7OuterAttemptCgroupCleanupV1Error,
                match="injected transient",
            ):
                acquired.close_unused()
            assert acquired.closed is False
            assert acquired.cleanup_state is (
                outer_v1.K7OuterAttemptCgroupLeaseStateV1.CLEANUP_PARTIAL
            )
            with pytest.raises(
                outer_v1.V075K7OuterAttemptCgroupV1Error,
                match="not consumable",
            ):
                _ = acquired.worker_fd
            with pytest.raises(
                outer_v1.V075K7OuterAttemptCgroupV1Error,
                match="not consumable",
            ):
                _ = acquired.outer_fd
            with pytest.raises(
                outer_v1.V075K7OuterAttemptCgroupV1Error,
                match="not consumable",
            ):
                acquired.to_document()
            acquired.close_unused()
        assert acquired.closed is True
        with pytest.raises(
            outer_v1.V075K7OuterAttemptCgroupV1Error,
            match="is closed",
        ):
            acquired.close_unused()

        changed_request = _successor_request("outer-real-control-change")
        changed_admission = admission_v1.probe_v075_k7_os_supervisor_admission_v1(
            delegated_parent_fd=parent_fd
        )
        changed_token = _issue(changed_request, changed_admission, parent_fd)
        changed = outer_v1.acquire_v075_k7_outer_attempt_cgroup_v1(
            request=changed_request,
            admission_result=changed_admission,
            delegated_parent_fd=parent_fd,
            nonce_token=changed_token,
        )
        assert type(changed) is outer_v1.K7OuterAttemptCgroupLeaseV1
        outer_v1.inner_v1._write_control(  # noqa: SLF001
            changed.worker_fd, "pids.max", "2"
        )
        with pytest.raises(
            outer_v1.V075K7OuterAttemptCgroupProtocolV1Error,
            match="removed after protocol mismatch",
        ) as protocol_error:
            changed.close_unused()
        assert protocol_error.value.cleanup_complete is True
        assert protocol_error.value.violations == ("worker_controls",)
        assert changed.closed is True
