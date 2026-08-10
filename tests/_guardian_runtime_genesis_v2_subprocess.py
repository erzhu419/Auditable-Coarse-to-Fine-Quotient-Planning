from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
import pickle
import shutil
import tempfile
import threading
import uuid

from acfqp import construction_k7_h1_e5a_runtime_lease_successor_v1 as b2a
from acfqp import construction_k7_h1_guardian_runtime_genesis_v2 as v2
from acfqp import construction_k7_h1_domain_registry_extension_v19 as domains_v19
from acfqp import construction_k7_h1_route_wide_working_set_cgroup_v1 as e5a
from acfqp import phase3e_ids as ids_v1


MIB = 1024 * 1024


def _future_consumer_preparation_only() -> None:
    raise AssertionError("registered preparation callable must not run in V2")


def _ident(label: str) -> str:
    return hashlib.sha256(f"guardian-v2-real:{label}".encode()).hexdigest()


def _write_at(directory_fd: int, name: str, raw: bytes) -> None:
    descriptor = os.open(name, os.O_WRONLY | os.O_CLOEXEC, dir_fd=directory_fd)
    try:
        offset = 0
        while offset < len(raw):
            written = os.write(descriptor, raw[offset:])
            if written <= 0:
                raise RuntimeError(f"short cgroup write: {name}")
            offset += written
    finally:
        os.close(descriptor)


def _open_dir_at(parent_fd: int, name: str) -> int:
    return os.open(
        name,
        os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW,
        dir_fd=parent_fd,
    )


def _current_scope_path() -> Path:
    relative = next(
        row.removeprefix("0::").strip()
        for row in Path("/proc/self/cgroup").read_text(encoding="ascii").splitlines()
        if row.startswith("0::")
    )
    return Path("/sys/fs/cgroup") / relative.lstrip("/")


class _DelegatedParents:
    def __init__(self) -> None:
        self.root_fd = -1
        self.guardian_fd = -1
        self.guardian_name = ""
        self._parents: list[tuple[str, int]] = []
        self._moved = False

    def __enter__(self) -> "_DelegatedParents":
        self.root_fd = os.open(
            _current_scope_path(),
            os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW,
        )
        suffix = f"{os.getpid()}-{uuid.uuid4().hex}"
        self.guardian_name = f"acfqp-v2-guardian-{suffix}"
        os.mkdir(self.guardian_name, mode=0o700, dir_fd=self.root_fd)
        self.guardian_fd = _open_dir_at(self.root_fd, self.guardian_name)
        _write_at(self.guardian_fd, "cgroup.procs", f"{os.getpid()}\n".encode())
        self._moved = True
        _write_at(self.root_fd, "cgroup.subtree_control", b"+memory +pids\n")
        return self

    def new_parent(self, ordinal: int) -> int:
        name = f"acfqp-v2-delegated-{ordinal}-{uuid.uuid4().hex}"
        os.mkdir(name, mode=0o700, dir_fd=self.root_fd)
        descriptor = _open_dir_at(self.root_fd, name)
        _write_at(descriptor, "cgroup.subtree_control", b"+memory +pids\n")
        self._parents.append((name, descriptor))
        return descriptor

    def __exit__(self, _kind, _value, _traceback) -> None:
        for name, descriptor in reversed(self._parents):
            try:
                if e5a._child_directories(descriptor):  # noqa: SLF001
                    raise RuntimeError(f"delegated parent was not cleaned: {name}")
            finally:
                os.close(descriptor)
            os.rmdir(name, dir_fd=self.root_fd)
        if self._moved:
            _write_at(self.root_fd, "cgroup.subtree_control", b"-memory -pids\n")
            _write_at(self.root_fd, "cgroup.procs", f"{os.getpid()}\n".encode())
        if self.guardian_fd >= 0:
            os.close(self.guardian_fd)
        if self.guardian_name:
            os.rmdir(self.guardian_name, dir_fd=self.root_fd)
        if self.root_fd >= 0:
            os.close(self.root_fd)


def _runtime(parent_fd: int, ordinal: int):
    lease = e5a.prepare_h1_route_wide_working_set_cgroup_v1(
        delegated_parent_cgroup_fd=parent_fd,
        registered_hard_cap_bytes=96 * MIB,
        requested_outer_memory_max_bytes=64 * MIB,
        logical_occurrence_id=_ident(f"occurrence:{ordinal}"),
        route_attempt_id=_ident(f"attempt:{ordinal}"),
        decision_point_id=_ident(f"decision:{ordinal}"),
        build_epoch_id=_ident(f"epoch:{ordinal}"),
    )
    return b2a.consume_h1_e5a_runtime_lease_successor_v1(lease)


def _journal(root: Path, name: str) -> Path:
    path = root / name
    path.mkdir(mode=0o700)
    return path


def _rejected_in_thread(operation) -> bool:
    result: list[bool] = []

    def target() -> None:
        try:
            operation()
        except v2.ConstructionK7H1GuardianRuntimeGenesisV2Error:
            result.append(True)
        else:
            result.append(False)

    thread = threading.Thread(target=target)
    thread.start()
    thread.join()
    return result == [True]


def _atfork_rejected(handle) -> bool:
    read_fd, write_fd = os.pipe2(os.O_CLOEXEC)
    child = os.fork()
    if child == 0:
        os.close(read_fd)
        try:
            try:
                v2.verify_h1_guardian_runtime_permit_handoff_v2(handle)
            except v2.ConstructionK7H1GuardianRuntimeGenesisV2Error:
                os.write(write_fd, b"1")
            else:
                os.write(write_fd, b"0")
        finally:
            os.close(write_fd)
            os._exit(0)
    os.close(write_fd)
    raw = os.read(read_fd, 2)
    os.close(read_fd)
    waited, status = os.waitpid(child, 0)
    return waited == child and os.waitstatus_to_exitcode(status) == 0 and raw == b"1"


def main() -> int:
    root = Path(tempfile.mkdtemp(prefix="acfqp-guardian-v2-real-", dir="/tmp"))
    root.chmod(0o700)
    result: dict[str, object] = {}
    try:
        with _DelegatedParents() as parents:
            # Exact B2-A PREPARED -> public V2 handoff -> durable revoke/cleanup.
            runtime = _runtime(parents.new_parent(1), 1)
            prereg = v2.preregister_h1_guardian_runtime_genesis_v2()
            journal = _journal(root, "basic")
            handle = v2.start_and_handoff_h1_guardian_runtime_genesis_v2(
                runtime, preregistration=prereg, journal_directory=journal
            )
            document = v2.verify_h1_guardian_runtime_permit_handoff_v2(handle)
            result["basic_handoff_state"] = handle.state
            result["basic_grant_count"] = len(document["grant_facts"])
            copy_attacks = 0
            for operation in (copy.copy, copy.deepcopy, pickle.dumps):
                try:
                    operation(handle)
                except v2.ConstructionK7H1GuardianRuntimeGenesisV2Error:
                    copy_attacks += 1
            result["copy_attack_count"] = copy_attacks
            adapter = v2.register_h1_guardian_runtime_consumer_adapter_v2(
                consumer_key="real-helper-preparation-v1",
                consumer_source_path=Path(__file__),
                consumer_callable=_future_consumer_preparation_only,
            )
            takeover = v2.prepare_h1_guardian_runtime_consumer_takeover_v2(
                handle,
                adapter=adapter,
                consumer_preparation_id=_ident("consumer-preparation"),
                launch_preparation_id=_ident("launch-preparation"),
            )
            takeover_document = takeover.to_document()
            result["takeover_prepared"] = (
                takeover_document["takeover_state"]
                == "PREPARED_UNCONSUMED_NONLAUNCHABLE"
                and takeover_document["consumer_invoked"] is False
                and handle.state == "HANDOFF_TAKEOVER_PREPARED_UNCONSUMED"
            )
            takeover_copy_attacks = 0
            for value in (adapter, takeover):
                for operation in (copy.copy, copy.deepcopy, pickle.dumps):
                    try:
                        operation(value)
                    except v2.ConstructionK7H1GuardianRuntimeGenesisV2Error:
                        takeover_copy_attacks += 1
            result["takeover_copy_attack_count"] = takeover_copy_attacks
            result["wrong_thread_verify_rejected"] = _rejected_in_thread(
                lambda: v2.verify_h1_guardian_runtime_permit_handoff_v2(handle)
            )
            result["wrong_thread_cancel_rejected"] = _rejected_in_thread(
                lambda: v2.cancel_h1_guardian_runtime_permit_handoff_v2(handle)
            )
            result["atfork_child_rejected"] = _atfork_rejected(handle)
            result["parent_survived_atfork"] = (
                v2.verify_h1_guardian_runtime_permit_handoff_v2(handle)[
                    "guardian_runtime_v2_public_handoff_id"
                ]
                == handle.handoff_id
            )

            saved_verify = v2._verify_live_record  # noqa: SLF001
            try:
                v2._verify_live_record = (  # type: ignore[assignment]  # noqa: SLF001
                    lambda _record: {"forged": True}
                )
                try:
                    v2.verify_h1_guardian_runtime_permit_handoff_v2(handle)
                except v2.ConstructionK7H1GuardianRuntimeGenesisV2Error:
                    result["local_callable_substitution_rejected"] = True
            finally:
                v2._verify_live_record = saved_verify  # noqa: SLF001

            record = v2._LIVE_HANDOFFS[id(handle)]  # noqa: SLF001
            original_candidate = record.candidates["BROKER"]
            record.candidates["BROKER"] = record.candidates["WORKER"]
            try:
                v2.verify_h1_guardian_runtime_permit_handoff_v2(handle)
            except v2.ConstructionK7H1GuardianRuntimeGenesisV2Error:
                result["grant_swap_rejected"] = True
            finally:
                record.candidates["BROKER"] = original_candidate

            original_fact = dict(record.grant_facts["BROKER"])
            record.grant_facts["BROKER"]["candidate_object_id"] = 0
            try:
                v2.verify_h1_guardian_runtime_permit_handoff_v2(handle)
            except v2.ConstructionK7H1GuardianRuntimeGenesisV2Error:
                result["identity_swap_rejected"] = True
            finally:
                record.grant_facts["BROKER"] = original_fact

            handoff_entry = record.entries["PUBLIC_HANDOFF"]
            artifact_path = journal / handoff_entry.filename
            original_raw = artifact_path.read_bytes()
            artifact_path.write_bytes(original_raw[:-1] + b" ")
            try:
                v2.verify_h1_guardian_runtime_permit_handoff_v2(handle)
            except v2.ConstructionK7H1GuardianRuntimeGenesisV2Error:
                result["journal_tamper_rejected"] = True
            finally:
                artifact_path.write_bytes(original_raw)

            cancellation = v2.cancel_h1_guardian_runtime_prepared_takeover_v2(takeover)
            verified = v2.verify_h1_guardian_runtime_cancellation_v2(cancellation)
            replay = v2.cancel_h1_guardian_runtime_permit_handoff_v2(handle)
            result["basic_cancellation_verified"] = (
                verified["process_birth_count"] == 0
                and verified["all_five_grants_closed"] is True
            )
            result["basic_cancel_replay_equal"] = replay is cancellation
            result["basic_runtime_state"] = runtime.state
            result["basic_journal_event_count"] = len(tuple(journal.iterdir()))
            original_cancellation_bytes = cancellation.canonical_bytes
            forged = cancellation.to_document()
            forged.pop("guardian_runtime_v2_cancellation_id")
            forged["terminal_code"] = "FORGED_TERMINAL"
            forged["b2a_runtime_cleanup_closure"] = {"forged": True}
            forged["guardian_runtime_v2_cancellation_id"] = (
                domains_v19.extension_content_id_v19(
                    domains_v19.CONSTRUCTION_K7_H1_GUARDIAN_RUNTIME_V2_CANCELLATION_V1_DOMAIN,
                    forged,
                )
            )
            object.__setattr__(
                cancellation, "canonical_bytes", ids_v1.canonical_json_bytes(forged)
            )
            try:
                v2.cancel_h1_guardian_runtime_permit_handoff_v2(handle)
            except v2.ConstructionK7H1GuardianRuntimeGenesisV2Error:
                result["terminal_replay_mutation_rejected"] = True
            try:
                v2.verify_h1_guardian_runtime_cancellation_v2(cancellation)
            except v2.ConstructionK7H1GuardianRuntimeGenesisV2Error:
                result["terminal_mutation_rejected"] = True
            finally:
                object.__setattr__(
                    cancellation, "canonical_bytes", original_cancellation_bytes
                )

            # A failed start is closed before publication and the same pristine
            # B2-A runtime can be retried through a fresh journal.
            retry_runtime = _runtime(parents.new_parent(2), 2)
            retry_prereg = v2.preregister_h1_guardian_runtime_genesis_v2()
            v2._TEST_ONLY_START_FAULT_AFTER_EVENT = "SOURCE_CLOSURE"  # noqa: SLF001
            try:
                v2.start_and_handoff_h1_guardian_runtime_genesis_v2(
                    retry_runtime,
                    preregistration=retry_prereg,
                    journal_directory=_journal(root, "start-fault"),
                )
            except RuntimeError:
                pass
            else:
                raise RuntimeError("start fault did not fire")
            finally:
                v2._TEST_ONLY_START_FAULT_AFTER_EVENT = None  # noqa: SLF001
            result["failure_closure_present"] = any(
                path.name.endswith("_FAILURE_CLOSURE.json")
                for path in (root / "start-fault").iterdir()
            )
            retry_handle = v2.start_and_handoff_h1_guardian_runtime_genesis_v2(
                retry_runtime,
                preregistration=retry_prereg,
                journal_directory=_journal(root, "start-retry"),
            )
            v2.cancel_h1_guardian_runtime_permit_handoff_v2(retry_handle)
            result["start_fault_runtime_reusable"] = retry_runtime.state == "CLOSED"

            # Partial grant issuance also converges and leaves no V2 reservation.
            partial_runtime = _runtime(parents.new_parent(3), 3)
            partial_prereg = v2.preregister_h1_guardian_runtime_genesis_v2()
            v2._TEST_ONLY_START_FAULT_AFTER_GRANT = 3  # noqa: SLF001
            try:
                v2.start_and_handoff_h1_guardian_runtime_genesis_v2(
                    partial_runtime,
                    preregistration=partial_prereg,
                    journal_directory=_journal(root, "partial-start-fault"),
                )
            except RuntimeError:
                pass
            else:
                raise RuntimeError("partial start fault did not fire")
            finally:
                v2._TEST_ONLY_START_FAULT_AFTER_GRANT = None  # noqa: SLF001
            partial_states = partial_runtime.grant_states()
            partial_failure = next(
                path
                for path in (root / "partial-start-fault").iterdir()
                if path.name.endswith("_FAILURE_CLOSURE.json")
            )
            partial_failure_document = json.loads(
                partial_failure.read_text(encoding="utf-8")
            )
            result["partial_start_fault_closed"] = (
                list(partial_states.values()).count("CONSUMED") == 3
                and partial_runtime.state == "CLOSED"
                and partial_failure_document["runtime_returned_to_pristine_prepared"]
                is False
                and partial_failure_document["runtime_and_e5a_hierarchy_closed"]
                is True
            )

            # Cancellation fault retains a typed cleanup handle and resumes.
            cancel_runtime = _runtime(parents.new_parent(4), 4)
            cancel_prereg = v2.preregister_h1_guardian_runtime_genesis_v2()
            cancel_handle = v2.start_and_handoff_h1_guardian_runtime_genesis_v2(
                cancel_runtime,
                preregistration=cancel_prereg,
                journal_directory=_journal(root, "cancel-fault"),
            )
            v2._TEST_ONLY_CANCEL_FAULT_AFTER_GRANT = 2  # noqa: SLF001
            try:
                v2.cancel_h1_guardian_runtime_permit_handoff_v2(cancel_handle)
            except v2.ConstructionK7H1GuardianRuntimeGenesisV2Error as error:
                if error.cleanup_handle is not cancel_handle:
                    raise
            else:
                raise RuntimeError("cancel fault did not fire")
            finally:
                v2._TEST_ONLY_CANCEL_FAULT_AFTER_GRANT = None  # noqa: SLF001
            result["cancel_fault_retryable_state"] = cancel_handle.state
            v2.cancel_h1_guardian_runtime_permit_handoff_v2(cancel_handle)
            result["cancel_fault_recovered"] = cancel_runtime.state == "CLOSED"

            # An uncertain directory fsync is finish-forward replayable rather
            # than becoming an O_EXCL fixed point.
            fsync_runtime = _runtime(parents.new_parent(5), 5)
            fsync_handle = v2.start_and_handoff_h1_guardian_runtime_genesis_v2(
                fsync_runtime,
                preregistration=v2.preregister_h1_guardian_runtime_genesis_v2(),
                journal_directory=_journal(root, "cancel-fsync-fault"),
            )
            original_fsync = v2.os.fsync
            fsync_count = 0

            def fail_second_fsync(descriptor: int) -> None:
                nonlocal fsync_count
                fsync_count += 1
                if fsync_count == 2:
                    raise OSError("injected directory fsync uncertainty")
                original_fsync(descriptor)

            v2.os.fsync = fail_second_fsync
            try:
                try:
                    v2.cancel_h1_guardian_runtime_permit_handoff_v2(fsync_handle)
                except v2.ConstructionK7H1GuardianRuntimeGenesisV2Error as error:
                    if error.cleanup_handle is not fsync_handle:
                        raise
            finally:
                v2.os.fsync = original_fsync
            v2.cancel_h1_guardian_runtime_permit_handoff_v2(fsync_handle)
            result["cancel_fsync_finish_forward"] = (
                fsync_runtime.state == "CLOSED"
                and id(fsync_runtime) not in v2._RUNTIME_RESERVATIONS  # noqa: SLF001
            )

            boundary_recovered = 0
            for ordinal, stage in enumerate(
                ("O_EXCL", "WRITE", "FILE_FSYNC", "DIR_FSYNC"), start=6
            ):
                boundary_runtime = _runtime(parents.new_parent(ordinal), ordinal)
                boundary_handle = v2.start_and_handoff_h1_guardian_runtime_genesis_v2(
                    boundary_runtime,
                    preregistration=v2.preregister_h1_guardian_runtime_genesis_v2(),
                    journal_directory=_journal(root, f"cancel-boundary-{stage.lower()}"),
                )
                v2._TEST_ONLY_JOURNAL_FAULT_EVENT = "UNCONSUMED_REVOKE"  # noqa: SLF001
                v2._TEST_ONLY_JOURNAL_FAULT_STAGE = stage  # noqa: SLF001
                try:
                    try:
                        v2.cancel_h1_guardian_runtime_permit_handoff_v2(
                            boundary_handle
                        )
                    except v2.ConstructionK7H1GuardianRuntimeGenesisV2Error as error:
                        if error.cleanup_handle is not boundary_handle:
                            raise
                finally:
                    v2._TEST_ONLY_JOURNAL_FAULT_EVENT = None  # noqa: SLF001
                    v2._TEST_ONLY_JOURNAL_FAULT_STAGE = None  # noqa: SLF001
                v2.cancel_h1_guardian_runtime_permit_handoff_v2(boundary_handle)
                if boundary_runtime.state == "CLOSED":
                    boundary_recovered += 1
            result["journal_boundary_finish_forward_count"] = boundary_recovered

            start_boundary_runtime = _runtime(parents.new_parent(10), 10)
            v2._TEST_ONLY_JOURNAL_FAULT_EVENT = "SOURCE_CLOSURE"  # noqa: SLF001
            v2._TEST_ONLY_JOURNAL_FAULT_STAGE = "DIR_FSYNC"  # noqa: SLF001
            v2._TEST_ONLY_SIGNAL_RESTORE_FAULT = True  # noqa: SLF001
            start_cleanup_handle = None
            compound_restore_failure = False
            try:
                v2.start_and_handoff_h1_guardian_runtime_genesis_v2(
                    start_boundary_runtime,
                    preregistration=v2.preregister_h1_guardian_runtime_genesis_v2(),
                    journal_directory=_journal(root, "start-boundary-dir-fsync"),
                )
            except v2.ConstructionK7H1GuardianRuntimeGenesisV2Error as error:
                start_cleanup_handle = error.cleanup_handle
                compound_restore_failure = (
                    isinstance(error.primary_error, RuntimeError)
                    and isinstance(error.cleanup_error, RuntimeError)
                    and isinstance(error.restoration_error, RuntimeError)
                )
            finally:
                v2._TEST_ONLY_JOURNAL_FAULT_EVENT = None  # noqa: SLF001
                v2._TEST_ONLY_JOURNAL_FAULT_STAGE = None  # noqa: SLF001
                v2._TEST_ONLY_SIGNAL_RESTORE_FAULT = False  # noqa: SLF001
            if start_cleanup_handle is None:
                raise RuntimeError("start boundary fault lost its cleanup handle")
            recovered_failure = v2.recover_h1_guardian_runtime_genesis_v2_failure_v1(
                start_cleanup_handle
            )
            start_boundary_handle = v2.start_and_handoff_h1_guardian_runtime_genesis_v2(
                start_boundary_runtime,
                preregistration=v2.preregister_h1_guardian_runtime_genesis_v2(),
                journal_directory=_journal(root, "start-boundary-retry"),
            )
            v2.cancel_h1_guardian_runtime_permit_handoff_v2(start_boundary_handle)
            result["start_boundary_finish_forward"] = (
                recovered_failure["runtime_returned_to_pristine_prepared"] is True
                and start_boundary_runtime.state == "CLOSED"
            )
            result["compound_restore_failure_recovered"] = (
                compound_restore_failure and start_boundary_handle.state == "CLOSED_CANCELLED_UNCONSUMED"
            )

            result["reservations_after_all_cases"] = len(  # noqa: SLF001
                v2._RUNTIME_RESERVATIONS
            )
        print(json.dumps(result, sort_keys=True, separators=(",", ":")))
        return 0
    finally:
        v2._TEST_ONLY_START_FAULT_AFTER_EVENT = None  # noqa: SLF001
        v2._TEST_ONLY_START_FAULT_AFTER_GRANT = None  # noqa: SLF001
        v2._TEST_ONLY_CANCEL_FAULT_AFTER_GRANT = None  # noqa: SLF001
        v2._TEST_ONLY_JOURNAL_FAULT_EVENT = None  # noqa: SLF001
        v2._TEST_ONLY_JOURNAL_FAULT_STAGE = None  # noqa: SLF001
        v2._TEST_ONLY_SIGNAL_RESTORE_FAULT = False  # noqa: SLF001
        shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
