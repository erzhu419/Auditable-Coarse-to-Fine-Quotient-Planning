from __future__ import annotations

from contextlib import contextmanager
import os
import pickle
from pathlib import Path
import threading

import pytest

from acfqp import v075_k7_os_supervisor_admission_v1 as admission_v1
from acfqp import v075_k7_outer_attempt_broker_preparation_v1 as prep_v1
from acfqp import v075_k7_outer_attempt_cgroup_v1 as outer_v1
from acfqp.phase3e_ids import PHASE3E_DOMAIN_TAGS, canonical_json_bytes
from tests.test_v075_k7_atomic_pidfd_runtime_v1 import _successor_request
from tests.test_v075_k7_parent_atomic_executor_v1 import (
    _delegated_scope_parent_fd,
)


def _write_controls(directory, values):
    directory.mkdir(exist_ok=True)
    defaults = {
        "cgroup.events": "populated 0\n",
        "cgroup.procs": "",
        "cgroup.threads": "",
        "cgroup.type": "domain\n",
        "cgroup.max.depth": "0\n",
        "cgroup.max.descendants": "0\n",
        "memory.peak": "0\n",
        "pids.current": "0\n",
        "pids.max": "1\n",
    }
    defaults.update(values)
    for name, value in defaults.items():
        (directory / name).write_text(value, encoding="ascii")


@contextmanager
def _fake_lease(tmp_path, monkeypatch, label, *, current="0\n"):
    parent = tmp_path / label
    outer = parent / "outer"
    worker = outer / "worker"
    worker.mkdir(parents=True)
    _write_controls(
        outer,
        {
            "cgroup.max.depth": "1\n",
            "cgroup.max.descendants": "2\n",
            "pids.max": "2\n",
            "memory.max": str(outer_v1.FIXED_OUTER_MEMORY_MAX_BYTES) + "\n",
            "memory.swap.max": "0\n",
            "cgroup.subtree_control": "memory pids\n",
            "cgroup.stat": "nr_descendants 1\nnr_dying_descendants 0\n",
            "cgroup.kill": "",
            "memory.current": current,
        },
    )
    _write_controls(worker, {})
    parent_fd = os.open(parent, os.O_RDONLY | os.O_DIRECTORY)
    outer_fd = os.open(outer, os.O_RDONLY | os.O_DIRECTORY)
    worker_fd = os.open(worker, os.O_RDONLY | os.O_DIRECTORY)
    peak_fd = os.open(outer / "memory.peak", os.O_RDWR)
    request = _successor_request(label)
    admission = admission_v1.probe_v075_k7_os_supervisor_admission_v1(
        delegated_parent_fd=parent_fd
    )
    lease = outer_v1.K7OuterAttemptCgroupLeaseV1(
        outer_v1._LEASE_ISSUER,  # noqa: SLF001
        parent_fd=parent_fd,
        outer_fd=outer_fd,
        worker_fd=worker_fd,
        outer_name="outer",
        worker_name="worker",
        request=request,
        admission_result=admission,
        broker_peak_fd=peak_fd,
        broker_peak_reset_peak=0,
        broker_peak_reset_current=0,
    )
    original_mkdir = os.mkdir
    original_rmdir = os.rmdir

    def fake_mkdir(path, mode=0o777, *, dir_fd=None):
        result = original_mkdir(path, mode=mode, dir_fd=dir_fd)
        if path == prep_v1.BUSINESS_NAME and dir_fd is not None:
            target = outer / prep_v1.BUSINESS_NAME
            _write_controls(target, {})
        return result

    def fake_rmdir(path, *, dir_fd=None):
        if dir_fd is not None:
            target = Path(os.path.realpath(f"/proc/self/fd/{dir_fd}")) / os.fspath(path)
        else:
            target = Path(os.fspath(path))
        target_path = Path(target)
        if target_path.is_dir():
            for child in tuple(target_path.iterdir()):
                if child.is_file():
                    child.unlink()
        return original_rmdir(path, dir_fd=dir_fd)

    def fake_stats(_descriptor):
        descendants = int(worker.exists()) + int((outer / "business").exists())
        return {"nr_descendants": descendants, "nr_dying_descendants": 0}

    monkeypatch.setattr(prep_v1.os, "mkdir", fake_mkdir)
    monkeypatch.setattr(prep_v1.os, "rmdir", fake_rmdir)
    monkeypatch.setattr(
        outer_v1.inner_v1,
        "_fstatfs_magic",
        lambda _descriptor: outer_v1.inner_v1.CGROUP2_SUPER_MAGIC,
    )
    monkeypatch.setattr(prep_v1.outer_v1, "_cgroup_stat", fake_stats)
    monkeypatch.setattr(
        prep_v1.outer_v1,
        "_wait_descendant_counts",
        lambda _descriptor, *, expected_descendants: (
            None
            if int(worker.exists()) + int((outer / "business").exists())
            == expected_descendants
            else (_ for _ in ()).throw(RuntimeError("descendants remain"))
        ),
    )
    yield lease, request, parent, outer, worker, fake_rmdir


def test_profile_is_prelaunch_only_and_domains_are_registered() -> None:
    assert prep_v1.PROPOSED_CONTRACT_VERSION == "2.0.5"
    assert prep_v1.LOCAL_DOMAIN_TAGS <= PHASE3E_DOMAIN_TAGS
    document = prep_v1.official_v075_k7_outer_attempt_broker_preparation_profile_v1().to_document()
    assert document["readiness_level"] == "PREPARED_LIVE_BROKER_SESSION"
    assert document["exact_measurement_window_reset_required"] == 0
    assert document["peak_reset_before_descendant_creation"] is True
    assert document["hierarchy_and_session_preparation_inside_memory_window"] is True
    assert document["prelaunch_peak_may_be_nonzero"] is True
    assert document["nonzero_baseline_subtraction_allowed"] is False
    assert document["same_memory_peak_open_file_description_required"] is True
    assert document["business_preidentity_cleanup_requires_parent_guard"] is True
    assert document["crash_persistent_cleanup_verified"] is False
    assert document["live_peer_role_ownership_verified"] is False
    assert document["launch_authority"] is False
    assert all(value is False for value in prep_v1._formal_locks().values())  # noqa: SLF001
    assert canonical_json_bytes(document)


def test_preparation_irreversibly_transfers_lease_and_rejects_replay(
    tmp_path, monkeypatch
) -> None:
    with _fake_lease(tmp_path, monkeypatch, "prepared-transfer") as (
        lease,
        _request,
        _parent,
        _outer,
        _worker,
        _rmdir,
    ):
        service = prep_v1.K7OuterAttemptBrokerPreparationServiceV1()
        session = service.prepare(lease)
        assert lease.cleanup_state is outer_v1.K7OuterAttemptCgroupLeaseStateV1.TRANSFERRED
        with pytest.raises(outer_v1.V075K7OuterAttemptCgroupV1Error):
            _ = lease.outer_fd
        with pytest.raises(outer_v1.V075K7OuterAttemptCgroupV1Error):
            lease.close_unused()
        with pytest.raises(
            prep_v1.V075K7OuterAttemptBrokerPreparationV1Error,
            match="already has",
        ):
            service.prepare(lease)
        document = session.to_document()
        assert document["processes_launched"] == 0
        assert document["ipc_frames_sent"] == 0
        assert document["shared_resource_value"] is None
        assert document["prelaunch_memory_peak"] >= document[
            "prelaunch_memory_current"
        ]
        assert document["baseline_subtraction_allowed"] is False
        assert session.binding.broker_execution_spec_id == session.execution_spec.spec_id
        assert len(session.binding.session_nonce) == 64
        spec_id = session.execution_spec.spec_id
        with pytest.raises(TypeError):
            session.execution_spec.parent_identity["inode"] = 0  # type: ignore[index]
        copied_spec = session.execution_spec.to_document()
        copied_spec["parent_descriptor_identity"]["inode"] = 0
        assert session.execution_spec.spec_id == spec_id
        assert session.execution_spec.to_document()[
            "parent_descriptor_identity"
        ]["inode"] != 0
        session.close_prelaunch()
        assert session.guardian.closed is True


def test_transferred_lease_context_exit_defers_to_guardian(
    tmp_path, monkeypatch
) -> None:
    with _fake_lease(tmp_path, monkeypatch, "prepared-context-transfer") as (
        lease,
        _request,
        parent,
        _outer,
        _worker,
        _rmdir,
    ):
        with lease:
            session = prep_v1.K7OuterAttemptBrokerPreparationServiceV1().prepare(
                lease
            )
        assert session.guardian.closed is False
        session.close_prelaunch()
        assert tuple(parent.iterdir()) == ()


def test_stale_handoff_token_cannot_claim_committed_guardian(
    tmp_path, monkeypatch
) -> None:
    with _fake_lease(tmp_path, monkeypatch, "prepared-stale-handoff") as (
        lease,
        _request,
        parent,
        _outer,
        _worker,
        _rmdir,
    ):
        session = prep_v1.K7OuterAttemptBrokerPreparationServiceV1().prepare(lease)
        assert lease._resolve_failed_broker_preparation_transfer(  # noqa: SLF001
            outer_v1._BROKER_PREPARATION_TRANSFER_ISSUER, object()  # noqa: SLF001
        ) is False
        assert lease._resolve_failed_broker_preparation_transfer(  # noqa: SLF001
            outer_v1._BROKER_PREPARATION_TRANSFER_ISSUER,
            session.guardian._transfer_token,  # noqa: SLF001
        ) is True
        assert session.guardian.closed is False
        session.close_prelaunch()
        assert tuple(parent.iterdir()) == ()


def test_guardian_constructor_failure_leaves_lease_cleanup_authority(
    tmp_path, monkeypatch
) -> None:
    with _fake_lease(tmp_path, monkeypatch, "prepared-constructor-failure") as (
        lease,
        _request,
        parent,
        _outer,
        _worker,
        _rmdir,
    ):
        monkeypatch.setattr(
            prep_v1,
            "K7OuterAttemptPrelaunchGuardianV1",
            lambda *_args, **_kwargs: (_ for _ in ()).throw(
                MemoryError("injected guardian construction failure")
            ),
        )
        with pytest.raises(
            prep_v1.V075K7OuterAttemptBrokerPreparationV1Error,
            match="before transfer",
        ):
            prep_v1.K7OuterAttemptBrokerPreparationServiceV1().prepare(lease)
        assert lease.closed is True
        assert tuple(parent.iterdir()) == ()


def test_prepare_and_unused_cleanup_race_has_one_cleanup_authority(
    tmp_path, monkeypatch
) -> None:
    with _fake_lease(tmp_path, monkeypatch, "prepared-cleanup-race") as (
        lease,
        _request,
        parent,
        _outer,
        _worker,
        _rmdir,
    ):
        service = prep_v1.K7OuterAttemptBrokerPreparationServiceV1()
        barrier = threading.Barrier(2)
        outcomes = []

        def prepare():
            barrier.wait()
            try:
                outcomes.append(("prepare", service.prepare(lease)))
            except BaseException as error:
                outcomes.append(("prepare_error", error))

        def close():
            barrier.wait()
            try:
                lease.close_unused()
                outcomes.append(("close", None))
            except BaseException as error:
                outcomes.append(("close_error", error))

        threads = (threading.Thread(target=prepare), threading.Thread(target=close))
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        sessions = [
            value
            for label, value in outcomes
            if label == "prepare"
            and type(value) is prep_v1.K7OuterAttemptPreparedBrokerSessionV1
        ]
        close_successes = [value for label, value in outcomes if label == "close"]
        assert len(sessions) + len(close_successes) == 1
        if sessions:
            sessions[0].close_prelaunch()
        assert tuple(parent.iterdir()) == ()


def test_issuer_owned_roles_cannot_be_minted_or_pickled() -> None:
    with pytest.raises(
        prep_v1.V075K7OuterAttemptBrokerPreparationV1Error,
        match="issuer-owned",
    ):
        prep_v1.K7OuterAttemptBrokerPreparationProfileV1(object())
    with pytest.raises(
        prep_v1.V075K7OuterAttemptBrokerPreparationV1Error,
        match="issuer-owned",
    ):
        prep_v1.K7OuterAttemptPrelaunchGuardianV1(object(), authority={})
    with pytest.raises(TypeError, match="unpickleable"):
        pickle.dumps(prep_v1.K7OuterAttemptBrokerPreparationServiceV1())


def test_cleanup_is_retryable_and_does_not_consult_stale_request(
    tmp_path, monkeypatch
) -> None:
    with _fake_lease(tmp_path, monkeypatch, "prepared-cleanup") as (
        lease,
        request,
        _parent,
        outer,
        worker,
        base_rmdir,
    ):
        session = prep_v1.K7OuterAttemptBrokerPreparationServiceV1().prepare(lease)
        failed = False

        def fail_worker_once(path, *, dir_fd=None):
            nonlocal failed
            if path == "worker" and not failed:
                failed = True
                raise OSError("injected worker deletion failure")
            return base_rmdir(path, dir_fd=dir_fd)

        monkeypatch.setattr(prep_v1.os, "rmdir", fail_worker_once)
        monkeypatch.setattr(
            type(request),
            "_assert_current",
            lambda _self: (_ for _ in ()).throw(RuntimeError("stale request")),
        )
        with pytest.raises(
            prep_v1.V075K7OuterAttemptBrokerPreparationV1Error,
            match="partial and retryable",
        ) as caught:
            session.close_prelaunch()
        assert caught.value.guardian is session.guardian
        assert not (outer / "business").exists()
        assert worker.exists()
        session.close_prelaunch()
        assert session.guardian.closed is True


def test_nonzero_or_inconsistent_reset_observation_fails_closed_and_consumes_request(
    tmp_path, monkeypatch
) -> None:
    with _fake_lease(
        tmp_path, monkeypatch, "prepared-bad-baseline", current="1\n"
    ) as (lease, _request, parent, _outer, _worker, _rmdir):
        service = prep_v1.K7OuterAttemptBrokerPreparationServiceV1()
        with pytest.raises(
            prep_v1.V075K7OuterAttemptBrokerPreparationV1Error,
            match="zero-reset",
        ):
            service.prepare(lease)
        assert tuple(parent.iterdir()) == ()
        with pytest.raises(
            prep_v1.V075K7OuterAttemptBrokerPreparationV1Error,
            match="already has",
        ):
            service.prepare(lease)


def test_control_mismatch_is_reported_after_complete_safe_cleanup(
    tmp_path, monkeypatch
) -> None:
    with _fake_lease(tmp_path, monkeypatch, "prepared-control-mismatch") as (
        lease,
        _request,
        parent,
        _outer,
        worker,
        _rmdir,
    ):
        session = prep_v1.K7OuterAttemptBrokerPreparationServiceV1().prepare(lease)
        (worker / "pids.max").write_text("2\n", encoding="ascii")
        with pytest.raises(
            prep_v1.V075K7OuterAttemptBrokerPreparationProtocolV1Error,
            match="removed after protocol mismatch",
        ) as caught:
            session.close_prelaunch()
        assert caught.value.cleanup_complete is True
        assert caught.value.violations == ("worker_controls",)
        assert session.guardian.closed is True
        assert tuple(parent.iterdir()) == ()


def test_control_mismatch_survives_partial_cleanup_retry(
    tmp_path, monkeypatch
) -> None:
    with _fake_lease(tmp_path, monkeypatch, "prepared-persistent-mismatch") as (
        lease,
        _request,
        _parent,
        outer,
        _worker,
        base_rmdir,
    ):
        session = prep_v1.K7OuterAttemptBrokerPreparationServiceV1().prepare(lease)
        (outer / "business" / "pids.max").write_text("2\n", encoding="ascii")
        failed = False

        def fail_worker_once(path, *, dir_fd=None):
            nonlocal failed
            if path == "worker" and not failed:
                failed = True
                raise OSError("injected worker deletion failure")
            return base_rmdir(path, dir_fd=dir_fd)

        monkeypatch.setattr(prep_v1.os, "rmdir", fail_worker_once)
        with pytest.raises(
            prep_v1.V075K7OuterAttemptBrokerPreparationV1Error,
            match="partial and retryable",
        ):
            session.close_prelaunch()
        with pytest.raises(
            prep_v1.V075K7OuterAttemptBrokerPreparationProtocolV1Error
        ) as caught:
            session.close_prelaunch()
        assert caught.value.cleanup_complete is True
        assert caught.value.violations == ("business_controls",)
        assert session.guardian.closed is True


def test_same_request_concurrent_preparation_has_one_winner(
    tmp_path, monkeypatch
) -> None:
    with _fake_lease(tmp_path, monkeypatch, "prepared-concurrent") as (
        lease,
        _request,
        _parent,
        _outer,
        _worker,
        _rmdir,
    ):
        service = prep_v1.K7OuterAttemptBrokerPreparationServiceV1()
        results = []

        def call():
            try:
                results.append(service.prepare(lease))
            except Exception as error:  # expected losing call
                results.append(error)

        threads = (threading.Thread(target=call), threading.Thread(target=call))
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        sessions = [
            result
            for result in results
            if type(result) is prep_v1.K7OuterAttemptPreparedBrokerSessionV1
        ]
        assert len(sessions) == 1
        assert any("already has" in str(result) for result in results if result not in sessions)
        sessions[0].close_prelaunch()


@pytest.mark.skipif(
    os.environ.get("ACFQP_RUN_REAL_CGROUP_INTEGRATION") != "1",
    reason="requires an externally prepared delegated systemd user scope",
)
def test_real_delegated_cgroup_prepares_and_closes_live_session() -> None:
    request = _successor_request("prepared-real")
    with _delegated_scope_parent_fd() as parent_fd:
        admission = admission_v1.probe_v075_k7_os_supervisor_admission_v1(
            delegated_parent_fd=parent_fd
        )
        nonce = outer_v1.official_v075_k7_outer_attempt_cgroup_nonce_service_v1().issue(
            request=request,
            admission_result=admission,
            delegated_parent_fd=parent_fd,
        )
        lease = outer_v1.acquire_v075_k7_outer_attempt_cgroup_v1(
            request=request,
            admission_result=admission,
            delegated_parent_fd=parent_fd,
            nonce_token=nonce,
        )
        assert type(lease) is outer_v1.K7OuterAttemptCgroupLeaseV1
        session = prep_v1.K7OuterAttemptBrokerPreparationServiceV1().prepare(lease)
        assert session.measurement_window_reset_memory_peak == 0
        assert session.measurement_window_reset_memory_current == 0
        assert session.prelaunch_memory_peak >= session.prelaunch_memory_current
        assert session.to_document()["baseline_subtraction_allowed"] is False
        session.close_prelaunch()
        assert session.guardian.closed is True
