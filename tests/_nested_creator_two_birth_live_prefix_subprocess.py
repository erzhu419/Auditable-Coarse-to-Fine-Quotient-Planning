from __future__ import annotations

import json
import os
from pathlib import Path
import signal
import sys
import threading
import time
import uuid

from acfqp import construction_k7_h1_nested_creator_probe_native_v1 as probe
from acfqp import construction_k7_h1_nested_creator_two_birth_runtime_v1 as runtime


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


def _read_at(directory_fd: int, name: str) -> bytes:
    descriptor = os.open(name, os.O_RDONLY | os.O_CLOEXEC, dir_fd=directory_fd)
    try:
        return os.read(descriptor, 65537)
    finally:
        os.close(descriptor)


def _wait_empty(directory_fd: int) -> None:
    deadline = time.monotonic() + 10.0
    while _read_at(directory_fd, "cgroup.procs"):
        if time.monotonic() >= deadline:
            raise RuntimeError("test cgroup did not empty")
        time.sleep(0.005)


def _current_scope_path() -> Path:
    relative = next(
        line.removeprefix("0::").strip()
        for line in Path("/proc/self/cgroup").read_text(encoding="ascii").splitlines()
        if line.startswith("0::")
    )
    return Path("/sys/fs/cgroup") / relative.lstrip("/")


def _direct_children() -> str:
    return Path(
        f"/proc/self/task/{threading.get_native_id()}/children"
    ).read_text(encoding="ascii").strip()


def _closed_summary(
    *,
    mode: str,
    control_fd: int,
    baseline_fd_count: int,
    baseline_subreaper: bool,
    extra: dict[str, object],
) -> dict[str, object]:
    empty = probe.observe_nested_creator_control_population_v1(
        control_fd, expected_pids=(), sequence=12001
    )
    return {
        "mode": mode,
        "final_population": empty["pids_current"],
        "fd_count_restored": len(os.listdir("/proc/self/fd"))
        == baseline_fd_count,
        "subreaper_restored": runtime._get_subreaper()  # noqa: SLF001
        == baseline_subreaper,
        "direct_children": _direct_children(),
        "outer_live_prefix_count": len(runtime._LIVE_PREFIXES),  # noqa: SLF001
        "inner_live_session_count": len(probe._LIVE_SESSIONS),  # noqa: SLF001
        "begin_failure_quarantine_present": (
            runtime._BEGIN_FAILURE_QUARANTINE is not None  # noqa: SLF001
        ),
        **extra,
    }


def _document_shape(value: object) -> object:
    if type(value) is dict:
        return {
            key: _document_shape(item)
            for key, item in sorted(value.items())
        }
    if type(value) is list:
        return [len(value), [_document_shape(item) for item in value]]
    if value is None:
        return "null"
    return type(value).__name__


def _static_closed_fields(document: dict[str, object]) -> dict[str, object]:
    dynamic_fact_fields = {
        "supervisor_pid",
        "supervisor_start_ticks",
        "probe_pid",
        "probe_start_ticks",
        "outer_pid_cell_value",
        "outer_parent_edge",
        "outer_nonce_hex",
        "outer_gate_facts",
        "outer_pidfd_fact",
        "outer_seal_set",
        "outer_role_source_fact",
        "outer_live_snapshots",
        "probe_facts",
        "supervisor_reap",
        "final_empty_snapshots",
    }
    return {
        key: value
        for key, value in document.items()
        if key not in dynamic_fact_fields
    }


def _fd_signature(descriptor: int) -> tuple[int, int, int]:
    status = os.fstat(descriptor)
    return status.st_dev, status.st_ino, status.st_mode


def _fd_is_closed(descriptor: int) -> bool:
    try:
        os.fstat(descriptor)
    except OSError:
        return True
    return False


def _run_mode(control_fd: int, mode: str) -> dict[str, object]:
    baseline_fd_count = len(os.listdir("/proc/self/fd"))
    baseline_subreaper = runtime._get_subreaper()  # noqa: SLF001
    baseline_signal_mask = signal.pthread_sigmask(signal.SIG_BLOCK, set())

    if mode == "AFTER_PREFIX_REGISTER":
        runtime._TEST_FAULT_PHASE = mode  # noqa: SLF001
        error_type = ""
        handle_returned = False
        try:
            returned = runtime.begin_bounded_nested_creator_two_birth_live_prefix_v1(
                control_cgroup_fd=control_fd
            )
            handle_returned = True
            runtime.abort_bounded_nested_creator_two_birth_live_prefix_v1(returned)
        except BaseException as error:
            error_type = type(error).__name__
        finally:
            runtime._TEST_FAULT_PHASE = None  # noqa: SLF001
        if not error_type:
            raise RuntimeError("AFTER_PREFIX_REGISTER did not fail")
        return _closed_summary(
            mode=mode,
            control_fd=control_fd,
            baseline_fd_count=baseline_fd_count,
            baseline_subreaper=baseline_subreaper,
            extra={
                "error_type": error_type,
                "handle_returned": handle_returned,
                "signal_mask_restored": (
                    signal.pthread_sigmask(signal.SIG_BLOCK, set())
                    == baseline_signal_mask
                ),
                "terminal_state": "NO_HANDLE_CLOSED",
            },
        )

    if mode == "BEGIN_CLEANUP_QUARANTINE_RECOVERY":
        original_abort = probe.abort_nested_creator_supervisor_session_v1
        abort_call_count = 0

        def fail_first_probe_abort(*args: object, **kwargs: object) -> object:
            nonlocal abort_call_count
            abort_call_count += 1
            if abort_call_count == 1:
                raise RuntimeError("injected begin cleanup abort failure")
            return original_abort(*args, **kwargs)

        probe.abort_nested_creator_supervisor_session_v1 = (  # type: ignore[assignment]
            fail_first_probe_abort
        )
        probe._TEST_FAULT_PHASE = "PROBE_PARENT_RETURN"  # noqa: SLF001
        begin_error_type = ""
        recovery: dict[str, object] | None = None
        try:
            try:
                runtime.begin_bounded_nested_creator_two_birth_live_prefix_v1(
                    control_cgroup_fd=control_fd
                )
            except BaseException as error:
                begin_error_type = type(error).__name__
            if not begin_error_type:
                raise RuntimeError("begin cleanup failure did not quarantine")
            quarantine = runtime._BEGIN_FAILURE_QUARANTINE  # noqa: SLF001
            quarantine_present_before_recovery = quarantine is not None
            quarantine_state_before_recovery = (
                quarantine.state if quarantine is not None else "ABSENT"
            )
            population_before_recovery = probe.observe_nested_creator_control_population_v1(
                control_fd,
                expected_pids=tuple(
                    int(value)
                    for value in _read_at(control_fd, "cgroup.procs").split()
                ),
                sequence=11601,
            )["pids_current"]
            recovery = runtime.recover_bounded_nested_creator_two_birth_begin_failure_v1()
        finally:
            probe.abort_nested_creator_supervisor_session_v1 = original_abort  # type: ignore[assignment]
            probe._TEST_FAULT_PHASE = None  # noqa: SLF001
        if recovery is None:
            raise RuntimeError("begin failure recovery did not return facts")
        return _closed_summary(
            mode=mode,
            control_fd=control_fd,
            baseline_fd_count=baseline_fd_count,
            baseline_subreaper=baseline_subreaper,
            extra={
                "begin_error_type": begin_error_type,
                "abort_call_count": abort_call_count,
                "quarantine_present_before_recovery": (
                    quarantine_present_before_recovery
                ),
                "quarantine_state_before_recovery": (
                    quarantine_state_before_recovery
                ),
                "population_before_recovery": population_before_recovery,
                "recovery_state": recovery["state"],
                "signal_mask_restored": (
                    signal.pthread_sigmask(signal.SIG_BLOCK, set())
                    == baseline_signal_mask
                ),
                "terminal_state": recovery["state"],
            },
        )

    if mode == "HIDDEN_BEGIN_CLEANUP_THREE_RECOVERIES":
        original_finish = runtime._finish_prefix_terminal  # noqa: SLF001
        finish_call_count = 0

        def fail_first_three_finishes(*args: object, **kwargs: object) -> object:
            nonlocal finish_call_count
            finish_call_count += 1
            if finish_call_count <= 3:
                raise RuntimeError("injected hidden begin cleanup failure")
            return original_finish(*args, **kwargs)

        runtime._finish_prefix_terminal = fail_first_three_finishes  # type: ignore[assignment]  # noqa: SLF001
        runtime._TEST_FAULT_PHASE = "AFTER_PREFIX_REGISTER"  # noqa: SLF001
        begin_error_type = ""
        recovery_errors: list[str] = []
        recovered: dict[str, object] | None = None
        try:
            try:
                runtime.begin_bounded_nested_creator_two_birth_live_prefix_v1(
                    control_cgroup_fd=control_fd
                )
            except BaseException as error:
                begin_error_type = type(error).__name__
            hidden_after_begin = [
                record.hidden_begin_failure
                for record in runtime._LIVE_PREFIXES.values()  # noqa: SLF001
            ]
            states_after_failed_recovery: list[str] = []
            for _ in range(2):
                try:
                    runtime.recover_bounded_nested_creator_two_birth_begin_failure_v1()
                except BaseException as error:
                    recovery_errors.append(type(error).__name__)
                states_after_failed_recovery.append(
                    next(
                        iter(runtime._LIVE_PREFIXES.values())  # noqa: SLF001
                    ).state
                )
            recovered = runtime.recover_bounded_nested_creator_two_birth_begin_failure_v1()
        finally:
            runtime._finish_prefix_terminal = original_finish  # type: ignore[assignment]  # noqa: SLF001
            runtime._TEST_FAULT_PHASE = None  # noqa: SLF001
        if recovered is None:
            raise RuntimeError("hidden begin cleanup did not recover")
        return _closed_summary(
            mode=mode,
            control_fd=control_fd,
            baseline_fd_count=baseline_fd_count,
            baseline_subreaper=baseline_subreaper,
            extra={
                "begin_error_type": begin_error_type,
                "finish_call_count": finish_call_count,
                "hidden_after_begin": hidden_after_begin,
                "recovery_error_types": recovery_errors,
                "states_after_failed_recovery": states_after_failed_recovery,
                "recovered_state": recovered["state"],
                "terminal_state": recovered["state"],
            },
        )

    if mode in {
        "AFTER_BEGIN_RECOVERY_CONTROL_CLOSE",
        "AFTER_BEGIN_RECOVERY_REGISTRY_CLEAR",
    }:
        original_abort = probe.abort_nested_creator_supervisor_session_v1
        abort_call_count = 0

        def fail_first_probe_abort(*args: object, **kwargs: object) -> object:
            nonlocal abort_call_count
            abort_call_count += 1
            if abort_call_count == 1:
                raise RuntimeError("injected begin cleanup abort failure")
            return original_abort(*args, **kwargs)

        probe.abort_nested_creator_supervisor_session_v1 = (  # type: ignore[assignment]
            fail_first_probe_abort
        )
        probe._TEST_FAULT_PHASE = "PROBE_PARENT_RETURN"  # noqa: SLF001
        begin_error_type = ""
        try:
            try:
                runtime.begin_bounded_nested_creator_two_birth_live_prefix_v1(
                    control_cgroup_fd=control_fd
                )
            except BaseException as error:
                begin_error_type = type(error).__name__
        finally:
            probe.abort_nested_creator_supervisor_session_v1 = original_abort  # type: ignore[assignment]
            probe._TEST_FAULT_PHASE = None  # noqa: SLF001
        if not begin_error_type:
            raise RuntimeError("begin recovery replay setup did not quarantine")
        runtime._TEST_FAULT_PHASE = mode  # noqa: SLF001
        first_recovery_error = ""
        try:
            runtime.recover_bounded_nested_creator_two_birth_begin_failure_v1()
        except BaseException as error:
            first_recovery_error = type(error).__name__
        finally:
            runtime._TEST_FAULT_PHASE = None  # noqa: SLF001
        if not first_recovery_error:
            raise RuntimeError(f"{mode} did not interrupt recovery")
        replayed = runtime.recover_bounded_nested_creator_two_birth_begin_failure_v1()
        return _closed_summary(
            mode=mode,
            control_fd=control_fd,
            baseline_fd_count=baseline_fd_count,
            baseline_subreaper=baseline_subreaper,
            extra={
                "begin_error_type": begin_error_type,
                "abort_call_count": abort_call_count,
                "first_recovery_error_type": first_recovery_error,
                "replayed_recovery_state": replayed["state"],
                "terminal_state": replayed["state"],
            },
        )

    if mode == "PENDING_SIGINT_FINAL_MASK_RESTORE":
        original_observe = probe.observe_nested_creator_control_population_v1
        sigint_send_count = 0

        def observe_with_pending_sigint(
            *args: object, **kwargs: object
        ) -> object:
            nonlocal sigint_send_count
            observed = original_observe(*args, **kwargs)
            if kwargs.get("sequence") == 7001 and sigint_send_count == 0:
                sigint_send_count += 1
                os.kill(os.getpid(), signal.SIGINT)
            return observed

        probe.observe_nested_creator_control_population_v1 = (  # type: ignore[assignment]
            observe_with_pending_sigint
        )
        begin_error_type = ""
        handle_returned = False
        try:
            try:
                runtime.begin_bounded_nested_creator_two_birth_live_prefix_v1(
                    control_cgroup_fd=control_fd
                )
                handle_returned = True
            except BaseException as error:
                begin_error_type = type(error).__name__
        finally:
            probe.observe_nested_creator_control_population_v1 = original_observe  # type: ignore[assignment]
        hidden_records = tuple(
            record
            for record in runtime._LIVE_PREFIXES.values()  # noqa: SLF001
            if record.hidden_begin_failure
        )
        hidden_states = [record.state for record in hidden_records]
        signal_mask_after_begin = signal.pthread_sigmask(signal.SIG_BLOCK, set())
        recovery = (
            runtime.recover_bounded_nested_creator_two_birth_begin_failure_v1()
        )
        return _closed_summary(
            mode=mode,
            control_fd=control_fd,
            baseline_fd_count=baseline_fd_count,
            baseline_subreaper=baseline_subreaper,
            extra={
                "sigint_send_count": sigint_send_count,
                "begin_error_type": begin_error_type,
                "handle_returned": handle_returned,
                "hidden_record_count": len(hidden_records),
                "hidden_states": hidden_states,
                "signal_mask_restored_after_begin": (
                    signal_mask_after_begin == baseline_signal_mask
                ),
                "recovery_state": recovery["state"],
                "terminal_state": recovery["state"],
            },
        )

    if mode == "BEGIN_QUARANTINE_UNRELATED_CHILD_GUARD":
        original_abort = probe.abort_nested_creator_supervisor_session_v1
        abort_call_count = 0

        def fail_first_probe_abort(*args: object, **kwargs: object) -> object:
            nonlocal abort_call_count
            abort_call_count += 1
            if abort_call_count == 1:
                raise RuntimeError("injected begin cleanup abort failure")
            return original_abort(*args, **kwargs)

        probe.abort_nested_creator_supervisor_session_v1 = (  # type: ignore[assignment]
            fail_first_probe_abort
        )
        probe._TEST_FAULT_PHASE = "PROBE_PARENT_RETURN"  # noqa: SLF001
        begin_error_type = ""
        try:
            try:
                runtime.begin_bounded_nested_creator_two_birth_live_prefix_v1(
                    control_cgroup_fd=control_fd
                )
            except BaseException as error:
                begin_error_type = type(error).__name__
        finally:
            probe.abort_nested_creator_supervisor_session_v1 = original_abort  # type: ignore[assignment]
            probe._TEST_FAULT_PHASE = None  # noqa: SLF001
        if not begin_error_type:
            raise RuntimeError("begin did not create a plain quarantine")

        read_fd, write_fd = os.pipe2(os.O_CLOEXEC)
        unrelated_pid = os.fork()
        if unrelated_pid == 0:
            os.close(write_fd)
            try:
                while os.read(read_fd, 1):
                    pass
            finally:
                os.close(read_fd)
            os._exit(0)
        os.close(read_fd)
        effect_calls = {"kill": 0, "waitid": 0, "inner_abort": 0}
        original_runtime_write = runtime._write_control  # noqa: SLF001
        original_probe_write = probe._write_control  # noqa: SLF001
        original_waitid = os.waitid
        original_recovery_abort = (
            probe.abort_nested_creator_supervisor_session_v1
        )

        def tracked_runtime_write(
            directory_fd: int, name: str, raw: bytes
        ) -> None:
            if name == "cgroup.kill":
                effect_calls["kill"] += 1
            original_runtime_write(directory_fd, name, raw)

        def tracked_probe_write(
            directory_fd: int, name: str, raw: bytes
        ) -> None:
            if name == "cgroup.kill":
                effect_calls["kill"] += 1
            original_probe_write(directory_fd, name, raw)

        def tracked_waitid(*args: object, **kwargs: object) -> object:
            effect_calls["waitid"] += 1
            return original_waitid(*args, **kwargs)

        def tracked_recovery_abort(*args: object, **kwargs: object) -> object:
            effect_calls["inner_abort"] += 1
            return original_recovery_abort(*args, **kwargs)

        runtime._write_control = tracked_runtime_write  # type: ignore[assignment]  # noqa: SLF001
        probe._write_control = tracked_probe_write  # type: ignore[assignment]  # noqa: SLF001
        os.waitid = tracked_waitid  # type: ignore[assignment]
        probe.abort_nested_creator_supervisor_session_v1 = (  # type: ignore[assignment]
            tracked_recovery_abort
        )
        rejection_error = ""
        try:
            try:
                runtime.recover_bounded_nested_creator_two_birth_begin_failure_v1()
            except BaseException as error:
                rejection_error = type(error).__name__
        finally:
            runtime._write_control = original_runtime_write  # type: ignore[assignment]  # noqa: SLF001
            probe._write_control = original_probe_write  # type: ignore[assignment]  # noqa: SLF001
            os.waitid = original_waitid  # type: ignore[assignment]
            probe.abort_nested_creator_supervisor_session_v1 = original_recovery_abort  # type: ignore[assignment]
        effects_before_caller_reap = dict(effect_calls)
        quarantine = runtime._BEGIN_FAILURE_QUARANTINE  # noqa: SLF001
        state_after_rejection = (
            quarantine.state if quarantine is not None else "ABSENT"
        )
        population_after_rejection = (
            probe.observe_nested_creator_control_population_v1(
                control_fd,
                expected_pids=tuple(
                    int(value)
                    for value in _read_at(control_fd, "cgroup.procs").split()
                ),
                sequence=11651,
            )["pids_current"]
        )
        os.close(write_fd)
        waited_pid, waited_status = os.waitpid(unrelated_pid, 0)
        recovery = (
            runtime.recover_bounded_nested_creator_two_birth_begin_failure_v1()
        )
        return _closed_summary(
            mode=mode,
            control_fd=control_fd,
            baseline_fd_count=baseline_fd_count,
            baseline_subreaper=baseline_subreaper,
            extra={
                "begin_error_type": begin_error_type,
                "abort_call_count": abort_call_count,
                "unrelated_pid": unrelated_pid,
                "rejection_error_type": rejection_error,
                "effects_before_caller_reap": effects_before_caller_reap,
                "state_after_rejection": state_after_rejection,
                "population_after_rejection": population_after_rejection,
                "unrelated_waited_pid": waited_pid,
                "unrelated_waited_exit_code": os.waitstatus_to_exitcode(
                    waited_status
                ),
                "recovery_state": recovery["state"],
                "terminal_state": recovery["state"],
            },
        )

    entry_fork_pid = -1
    entry_fork_exit_code = -1
    entry_fork_count = 0
    original_observe = probe.observe_nested_creator_control_population_v1

    def observe_with_entry_fork(*args: object, **kwargs: object) -> object:
        nonlocal entry_fork_pid, entry_fork_exit_code, entry_fork_count
        if kwargs.get("sequence") == 7000 and entry_fork_count == 0:
            entry_fork_count += 1
            entry_fork_pid = os.fork()
            if entry_fork_pid == 0:
                os._exit(191)
            waited_pid, status = os.waitpid(entry_fork_pid, 0)
            if waited_pid != entry_fork_pid:
                raise RuntimeError("construction entry fork child identity changed")
            entry_fork_exit_code = os.waitstatus_to_exitcode(status)
        return original_observe(*args, **kwargs)

    if mode == "BEGIN_ENTRY_FORK":
        probe.observe_nested_creator_control_population_v1 = (  # type: ignore[assignment]
            observe_with_entry_fork
        )
    try:
        handle = runtime.begin_bounded_nested_creator_two_birth_live_prefix_v1(
            control_cgroup_fd=control_fd
        )
    finally:
        probe.observe_nested_creator_control_population_v1 = original_observe  # type: ignore[assignment]
    signal_mask_after_begin = signal.pthread_sigmask(signal.SIG_BLOCK, set())
    live_snapshot = probe.observe_nested_creator_control_population_v1(
        control_fd,
        expected_pids=(handle.supervisor_pid,),
        sequence=11001,
    )
    common = {
        "live_state": handle.state,
        "live_population": live_snapshot["pids_current"],
        "supervisor_pid": handle.supervisor_pid,
        "probe_pid": handle.probe_pid,
        "fd_delta_while_live": len(os.listdir("/proc/self/fd"))
        - baseline_fd_count,
        "subreaper_while_live": runtime._get_subreaper(),  # noqa: SLF001
        "signal_mask_restored_after_begin": signal_mask_after_begin
        == baseline_signal_mask,
        "outer_live_prefix_count_while_live": len(
            runtime._LIVE_PREFIXES  # noqa: SLF001
        ),
        "inner_live_session_count_while_live": len(
            probe._LIVE_SESSIONS  # noqa: SLF001
        ),
        "v2_raw_facts_identity_retained": (
            handle.probe_observed_facts_v2.raw_facts_v1
            is handle.probe_facts
        ),
        "v2_schema": handle.probe_observed_facts_v2.to_document()["schema"],
        "v2_protocol_receive_observation_count": len(
            handle.probe_observed_facts_v2.protocol_receive_observations
        ),
    }

    if mode == "ATFORK":
        session = handle._nested_session  # noqa: SLF001
        live_descriptors = (
            handle._control_cgroup_fd,  # noqa: SLF001
            session.control_fd,
            session.supervisor_pidfd,
        )
        if len(set(live_descriptors)) != 3 or min(live_descriptors) < 0:
            raise RuntimeError("live prefix did not retain three distinct FDs")
        parent_fd_signatures = tuple(
            _fd_signature(descriptor) for descriptor in live_descriptors
        )
        effect_calls = {"kill": 0, "reap": 0, "subreaper": 0}
        original_runtime_write = runtime._write_control  # noqa: SLF001
        original_probe_write = probe._write_control  # noqa: SLF001
        original_waitid = os.waitid
        original_set_subreaper = runtime._set_subreaper  # noqa: SLF001

        def tracked_runtime_write(
            directory_fd: int, name: str, raw: bytes
        ) -> None:
            if name == "cgroup.kill":
                effect_calls["kill"] += 1
            original_runtime_write(directory_fd, name, raw)

        def tracked_probe_write(
            directory_fd: int, name: str, raw: bytes
        ) -> None:
            if name == "cgroup.kill":
                effect_calls["kill"] += 1
            original_probe_write(directory_fd, name, raw)

        def tracked_waitid(*args: object, **kwargs: object) -> object:
            effect_calls["reap"] += 1
            return original_waitid(*args, **kwargs)

        def tracked_set_subreaper(enabled: bool) -> None:
            effect_calls["subreaper"] += 1
            original_set_subreaper(enabled)

        runtime._write_control = tracked_runtime_write  # type: ignore[assignment]  # noqa: SLF001
        probe._write_control = tracked_probe_write  # type: ignore[assignment]  # noqa: SLF001
        os.waitid = tracked_waitid  # type: ignore[assignment]
        runtime._set_subreaper = tracked_set_subreaper  # type: ignore[assignment]  # noqa: SLF001
        read_fd, write_fd = os.pipe2(os.O_CLOEXEC)
        child_pid = os.fork()
        if child_pid == 0:
            os.close(read_fd)
            try:
                close_error = abort_error = ""
                try:
                    runtime.close_bounded_nested_creator_two_birth_live_prefix_v1(
                        handle
                    )
                except BaseException as error:
                    close_error = type(error).__name__
                try:
                    runtime.abort_bounded_nested_creator_two_birth_live_prefix_v1(
                        handle
                    )
                except BaseException as error:
                    abort_error = type(error).__name__
                child_live_snapshot = (
                    probe.observe_nested_creator_control_population_v1(
                        control_fd,
                        expected_pids=(handle.supervisor_pid,),
                        sequence=11501,
                    )
                )
                child_document: dict[str, object] = {
                    "outer_registry_empty": len(runtime._LIVE_PREFIXES) == 0,  # noqa: SLF001
                    "inner_registry_empty": len(probe._LIVE_SESSIONS) == 0,  # noqa: SLF001
                    "handle_state": handle.state,
                    "session_state": session.state,
                    "handle_control_fd_field": handle._control_cgroup_fd,  # noqa: SLF001
                    "session_control_fd_field": session.control_fd,
                    "session_pidfd_field": session.supervisor_pidfd,
                    "inherited_fds_closed": [
                        _fd_is_closed(descriptor)
                        for descriptor in live_descriptors
                    ],
                    "close_error_type": close_error,
                    "abort_error_type": abort_error,
                    "effect_calls": dict(effect_calls),
                    "supervisor_still_live": (
                        child_live_snapshot["pids_current"] == 1
                    ),
                    "direct_children": _direct_children(),
                }
            except BaseException as error:
                child_document = {
                    "child_internal_error": repr(error),
                }
            raw = json.dumps(
                child_document, sort_keys=True, separators=(",", ":")
            ).encode("utf-8")
            os.write(write_fd, raw)
            os.close(write_fd)
            os._exit(0)

        os.close(write_fd)
        chunks: list[bytes] = []
        while True:
            chunk = os.read(read_fd, 65536)
            if not chunk:
                break
            chunks.append(chunk)
        os.close(read_fd)
        waited_pid, wait_status = os.waitpid(child_pid, 0)
        child_document = json.loads(b"".join(chunks))
        parent_atfork_effect_calls = dict(effect_calls)
        parent_fd_signatures_after = tuple(
            _fd_signature(descriptor) for descriptor in live_descriptors
        )
        parent_snapshot = probe.observe_nested_creator_control_population_v1(
            control_fd,
            expected_pids=(handle.supervisor_pid,),
            sequence=11502,
        )
        parent_live_facts = {
            "child_pid": child_pid,
            "child_wait_pid": waited_pid,
            "child_wait_exited_zero": os.waitstatus_to_exitcode(wait_status) == 0,
            "child_document": child_document,
            "parent_outer_registry_intact": (
                getattr(
                    runtime._LIVE_PREFIXES.get(id(handle)),  # noqa: SLF001
                    "handle",
                    None,
                )
                is handle
            ),
            "parent_inner_registry_intact": (
                probe._LIVE_SESSIONS.get(id(session)) is session  # noqa: SLF001
            ),
            "parent_handle_state_after_fork": handle.state,
            "parent_session_state_after_fork": session.state,
            "parent_live_fds_unchanged": (
                parent_fd_signatures_after == parent_fd_signatures
            ),
            "parent_effect_calls_during_fork": parent_atfork_effect_calls,
            "parent_supervisor_still_live": parent_snapshot["pids_current"] == 1,
            "parent_subreaper_unchanged_during_fork": (
                runtime._get_subreaper()  # noqa: SLF001
                == common["subreaper_while_live"]
            ),
        }
        runtime._write_control = original_runtime_write  # type: ignore[assignment]  # noqa: SLF001
        probe._write_control = original_probe_write  # type: ignore[assignment]  # noqa: SLF001
        os.waitid = original_waitid  # type: ignore[assignment]
        runtime._set_subreaper = original_set_subreaper  # type: ignore[assignment]  # noqa: SLF001
        result = runtime.close_bounded_nested_creator_two_birth_live_prefix_v1(
            handle
        )
        return _closed_summary(
            mode=mode,
            control_fd=control_fd,
            baseline_fd_count=baseline_fd_count,
            baseline_subreaper=baseline_subreaper,
            extra={
                **common,
                **parent_live_facts,
                "terminal_state": handle.state,
                "result_supervisor_pid": result.supervisor_pid,
            },
        )

    if mode == "BEGIN_ENTRY_FORK":
        result = runtime.close_bounded_nested_creator_two_birth_live_prefix_v1(
            handle
        )
        return _closed_summary(
            mode=mode,
            control_fd=control_fd,
            baseline_fd_count=baseline_fd_count,
            baseline_subreaper=baseline_subreaper,
            extra={
                **common,
                "entry_fork_count": entry_fork_count,
                "entry_fork_pid": entry_fork_pid,
                "entry_fork_exit_code": entry_fork_exit_code,
                "terminal_state": handle.state,
                "result_supervisor_pid": result.supervisor_pid,
            },
        )

    if mode == "UNRELATED_CHILD_ABORT_GUARD":
        read_fd, write_fd = os.pipe2(os.O_CLOEXEC)
        unrelated_pid = os.fork()
        if unrelated_pid == 0:
            os.close(write_fd)
            try:
                while os.read(read_fd, 1):
                    pass
            finally:
                os.close(read_fd)
            os._exit(0)
        os.close(read_fd)
        effect_calls = {"kill": 0, "waitid": 0, "inner_abort": 0}
        original_runtime_write = runtime._write_control  # noqa: SLF001
        original_probe_write = probe._write_control  # noqa: SLF001
        original_waitid = os.waitid
        original_inner_abort = probe.abort_nested_creator_supervisor_session_v1

        def tracked_runtime_write(
            directory_fd: int, name: str, raw: bytes
        ) -> None:
            if name == "cgroup.kill":
                effect_calls["kill"] += 1
            original_runtime_write(directory_fd, name, raw)

        def tracked_probe_write(
            directory_fd: int, name: str, raw: bytes
        ) -> None:
            if name == "cgroup.kill":
                effect_calls["kill"] += 1
            original_probe_write(directory_fd, name, raw)

        def tracked_waitid(*args: object, **kwargs: object) -> object:
            effect_calls["waitid"] += 1
            return original_waitid(*args, **kwargs)

        def tracked_inner_abort(*args: object, **kwargs: object) -> object:
            effect_calls["inner_abort"] += 1
            return original_inner_abort(*args, **kwargs)

        runtime._write_control = tracked_runtime_write  # type: ignore[assignment]  # noqa: SLF001
        probe._write_control = tracked_probe_write  # type: ignore[assignment]  # noqa: SLF001
        os.waitid = tracked_waitid  # type: ignore[assignment]
        probe.abort_nested_creator_supervisor_session_v1 = (  # type: ignore[assignment]
            tracked_inner_abort
        )
        rejection_error = ""
        try:
            try:
                runtime.abort_bounded_nested_creator_two_birth_live_prefix_v1(
                    handle
                )
            except BaseException as error:
                rejection_error = type(error).__name__
        finally:
            runtime._write_control = original_runtime_write  # type: ignore[assignment]  # noqa: SLF001
            probe._write_control = original_probe_write  # type: ignore[assignment]  # noqa: SLF001
            os.waitid = original_waitid  # type: ignore[assignment]
            probe.abort_nested_creator_supervisor_session_v1 = original_inner_abort  # type: ignore[assignment]
        effects_before_caller_reap = dict(effect_calls)
        state_after_rejection = handle.state
        population_after_rejection = (
            probe.observe_nested_creator_control_population_v1(
                control_fd,
                expected_pids=(handle.supervisor_pid,),
                sequence=11551,
            )["pids_current"]
        )
        os.close(write_fd)
        waited_pid, waited_status = os.waitpid(unrelated_pid, 0)
        abort_facts = (
            runtime.abort_bounded_nested_creator_two_birth_live_prefix_v1(
                handle
            )
        )
        return _closed_summary(
            mode=mode,
            control_fd=control_fd,
            baseline_fd_count=baseline_fd_count,
            baseline_subreaper=baseline_subreaper,
            extra={
                **common,
                "unrelated_pid": unrelated_pid,
                "rejection_error_type": rejection_error,
                "effects_before_caller_reap": effects_before_caller_reap,
                "state_after_rejection": state_after_rejection,
                "population_after_rejection": population_after_rejection,
                "unrelated_waited_pid": waited_pid,
                "unrelated_waited_exit_code": os.waitstatus_to_exitcode(
                    waited_status
                ),
                "abort_state": abort_facts["state"],
                "terminal_state": handle.state,
            },
        )

    if mode in {"AFTER_CONTROL_CLOSE", "AFTER_REGISTRY_DELETE"}:
        runtime._TEST_FAULT_PHASE = mode  # noqa: SLF001
        first_close_error = ""
        try:
            runtime.close_bounded_nested_creator_two_birth_live_prefix_v1(
                handle
            )
        except BaseException as error:
            first_close_error = type(error).__name__
        finally:
            runtime._TEST_FAULT_PHASE = None  # noqa: SLF001
        if not first_close_error:
            raise RuntimeError(f"{mode} did not interrupt terminal commit")
        state_after_interruption = handle.state
        if state_after_interruption == "CLOSED":
            replay = runtime.close_bounded_nested_creator_two_birth_live_prefix_v1(
                handle
            )
            replay_kind = type(replay).__name__
        elif state_after_interruption == "ABORTED_CLOSED":
            replay = runtime.abort_bounded_nested_creator_two_birth_live_prefix_v1(
                handle
            )
            replay_kind = replay["state"]
        else:
            raise RuntimeError("terminal interruption did not close on replay")
        return _closed_summary(
            mode=mode,
            control_fd=control_fd,
            baseline_fd_count=baseline_fd_count,
            baseline_subreaper=baseline_subreaper,
            extra={
                **common,
                "first_close_error_type": first_close_error,
                "state_after_interruption": state_after_interruption,
                "replay_kind": replay_kind,
                "terminal_state": handle.state,
            },
        )

    if mode == "HANDLE_PRIVATE_TAMPER":
        original_public = {
            "supervisor_pid": handle.supervisor_pid,
            "supervisor_start_ticks": handle.supervisor_start_ticks,
            "probe_pid": handle.probe_pid,
            "probe_start_ticks": handle.probe_start_ticks,
            "state": handle.state,
            "probe_facts": handle.probe_facts,
            "probe_observed_facts_v2": handle.probe_observed_facts_v2,
        }
        handle._supervisor_pid = -101  # noqa: SLF001
        handle._supervisor_start_ticks = -102  # noqa: SLF001
        handle._probe_pid = -103  # noqa: SLF001
        handle._probe_start_ticks = -104  # noqa: SLF001
        handle._state = "CALLER_TAMPERED"  # noqa: SLF001
        handle._probe_facts = object()  # type: ignore[assignment]  # noqa: SLF001
        handle._probe_observed_facts_v2 = object()  # type: ignore[assignment]  # noqa: SLF001
        handle._control_cgroup_fd = -105  # noqa: SLF001
        handle._owner_pid = -106  # noqa: SLF001
        handle._issuer = object()  # noqa: SLF001
        public_record_authoritative = (
            handle.supervisor_pid == original_public["supervisor_pid"]
            and handle.supervisor_start_ticks
            == original_public["supervisor_start_ticks"]
            and handle.probe_pid == original_public["probe_pid"]
            and handle.probe_start_ticks == original_public["probe_start_ticks"]
            and handle.state == original_public["state"]
            and handle.probe_facts is original_public["probe_facts"]
            and handle.probe_observed_facts_v2
            is original_public["probe_observed_facts_v2"]
        )
        result = runtime.close_bounded_nested_creator_two_birth_live_prefix_v1(
            handle
        )
        return _closed_summary(
            mode=mode,
            control_fd=control_fd,
            baseline_fd_count=baseline_fd_count,
            baseline_subreaper=baseline_subreaper,
            extra={
                **common,
                "public_record_authoritative": public_record_authoritative,
                "terminal_state": handle.state,
                "result_supervisor_pid": result.supervisor_pid,
                "expected_supervisor_pid": original_public["supervisor_pid"],
            },
        )

    if mode in {
        "AFTER_SHUTDOWN_ECHO",
        "AFTER_SUPERVISOR_REAP",
        "BEFORE_SUBREAPER_RESTORE",
    }:
        runtime._TEST_FAULT_PHASE = mode  # noqa: SLF001
        error_type = ""
        try:
            runtime.close_bounded_nested_creator_two_birth_live_prefix_v1(
                handle
            )
        except BaseException as error:
            error_type = type(error).__name__
        finally:
            runtime._TEST_FAULT_PHASE = None  # noqa: SLF001
        if not error_type:
            raise RuntimeError(f"{mode} did not fail")
        return _closed_summary(
            mode=mode,
            control_fd=control_fd,
            baseline_fd_count=baseline_fd_count,
            baseline_subreaper=baseline_subreaper,
            extra={
                **common,
                "error_type": error_type,
                "terminal_state": handle.state,
            },
        )

    if mode == "ABORT_QUARANTINE_RETRY":
        original_finish = runtime._finish_prefix_terminal  # noqa: SLF001
        finish_call_count = 0

        def fail_first_finish(*args: object, **kwargs: object) -> object:
            nonlocal finish_call_count
            finish_call_count += 1
            if finish_call_count == 1:
                raise RuntimeError("injected abort terminal failure")
            return original_finish(*args, **kwargs)

        runtime._finish_prefix_terminal = fail_first_finish  # type: ignore[assignment]  # noqa: SLF001
        first_error_type = ""
        retry_facts: dict[str, object] | None = None
        try:
            try:
                runtime.abort_bounded_nested_creator_two_birth_live_prefix_v1(
                    handle
                )
            except BaseException as error:
                first_error_type = type(error).__name__
            if not first_error_type:
                raise RuntimeError("abort quarantine injection did not fail")
            quarantined_state = handle.state
            quarantined_outer_registry_count = len(
                runtime._LIVE_PREFIXES  # noqa: SLF001
            )
            quarantined_inner_registry_count = len(
                probe._LIVE_SESSIONS  # noqa: SLF001
            )
            quarantined_population = probe.observe_nested_creator_control_population_v1(
                control_fd, expected_pids=(), sequence=11701
            )["pids_current"]
            quarantined_fd_delta = len(os.listdir("/proc/self/fd")) - baseline_fd_count
            retry_facts = runtime.abort_bounded_nested_creator_two_birth_live_prefix_v1(
                handle
            )
        finally:
            runtime._finish_prefix_terminal = original_finish  # type: ignore[assignment]  # noqa: SLF001
        if retry_facts is None:
            raise RuntimeError("abort quarantine retry did not return facts")
        return _closed_summary(
            mode=mode,
            control_fd=control_fd,
            baseline_fd_count=baseline_fd_count,
            baseline_subreaper=baseline_subreaper,
            extra={
                **common,
                "first_error_type": first_error_type,
                "finish_call_count": finish_call_count,
                "quarantined_state": quarantined_state,
                "quarantined_outer_registry_count": (
                    quarantined_outer_registry_count
                ),
                "quarantined_inner_registry_count": (
                    quarantined_inner_registry_count
                ),
                "quarantined_population": quarantined_population,
                "quarantined_fd_delta": quarantined_fd_delta,
                "retry_state": retry_facts["state"],
                "terminal_state": handle.state,
            },
        )

    if mode == "BEGIN_CLOSE":
        retained_v2 = handle.probe_observed_facts_v2
        retained_v2_document = retained_v2.to_document()
        result = runtime.close_bounded_nested_creator_two_birth_live_prefix_v1(
            handle
        )
        repeated_result = (
            runtime.close_bounded_nested_creator_two_birth_live_prefix_v1(handle)
        )
        abort_after_close_error = ""
        try:
            runtime.abort_bounded_nested_creator_two_birth_live_prefix_v1(handle)
        except BaseException as error:
            abort_after_close_error = type(error).__name__
        if not abort_after_close_error:
            raise RuntimeError("abort-after-close unexpectedly succeeded")
        document = result.to_document()
        legacy_result = runtime.run_bounded_nested_creator_two_birth_runtime_v1(
            control_cgroup_fd=control_fd
        )
        legacy_document = legacy_result.to_document()
        return _closed_summary(
            mode=mode,
            control_fd=control_fd,
            baseline_fd_count=baseline_fd_count,
            baseline_subreaper=baseline_subreaper,
            extra={
                **common,
                "terminal_state": handle.state,
                "result_type": type(result).__name__,
                "result_schema": document["schema"],
                "result_supervisor_pid": document["supervisor_pid"],
                "result_probe_pid": document["probe_pid"],
                "result_final_population": document["final_empty_snapshots"][0][
                    "pids_current"
                ],
                "result_birth_order": document["birth_order"],
                "repeated_close_same_result": repeated_result is result,
                "abort_after_close_error_type": abort_after_close_error,
                "v2_identity_retained_after_close": (
                    handle.probe_observed_facts_v2 is retained_v2
                ),
                "v2_document_retained_after_close": (
                    handle.probe_observed_facts_v2.to_document()
                    == retained_v2_document
                ),
                "legacy_result_type": type(legacy_result).__name__,
                "legacy_document_shape_equal": (
                    _document_shape(legacy_document)
                    == _document_shape(document)
                ),
                "legacy_static_fields_equal": (
                    _static_closed_fields(legacy_document)
                    == _static_closed_fields(document)
                ),
                "legacy_dynamic_identities_distinct": (
                    legacy_document["supervisor_pid"]
                    != document["supervisor_pid"]
                    and legacy_document["probe_pid"] != document["probe_pid"]
                    and legacy_document["outer_nonce_hex"]
                    != document["outer_nonce_hex"]
                ),
                "legacy_final_population": legacy_document[
                    "final_empty_snapshots"
                ][0]["pids_current"],
            },
        )

    if mode == "EXPLICIT_ABORT":
        abort_facts = runtime.abort_bounded_nested_creator_two_birth_live_prefix_v1(
            handle
        )
        repeated_abort_facts = (
            runtime.abort_bounded_nested_creator_two_birth_live_prefix_v1(handle)
        )
        close_after_abort_error = ""
        try:
            runtime.close_bounded_nested_creator_two_birth_live_prefix_v1(handle)
        except BaseException as error:
            close_after_abort_error = type(error).__name__
        if not close_after_abort_error:
            raise RuntimeError("close-after-abort unexpectedly succeeded")
        return _closed_summary(
            mode=mode,
            control_fd=control_fd,
            baseline_fd_count=baseline_fd_count,
            baseline_subreaper=baseline_subreaper,
            extra={
                **common,
                "terminal_state": handle.state,
                "abort_state": abort_facts["state"],
                "repeated_abort_facts_equal": repeated_abort_facts == abort_facts,
                "close_after_abort_error_type": close_after_abort_error,
            },
        )

    if mode == "WRONG_THREAD":
        errors: list[str] = []

        def wrong_owner_close() -> None:
            try:
                runtime.close_bounded_nested_creator_two_birth_live_prefix_v1(
                    handle
                )
            except BaseException as error:  # test process must retain exact type
                errors.append(type(error).__name__)

        thread = threading.Thread(target=wrong_owner_close)
        thread.start()
        thread.join(timeout=10)
        if thread.is_alive() or len(errors) != 1:
            raise RuntimeError("wrong-owner close did not fail exactly once")
        state_after_rejection = handle.state
        result = runtime.close_bounded_nested_creator_two_birth_live_prefix_v1(
            handle
        )
        return _closed_summary(
            mode=mode,
            control_fd=control_fd,
            baseline_fd_count=baseline_fd_count,
            baseline_subreaper=baseline_subreaper,
            extra={
                **common,
                "wrong_thread_error_type": errors[0],
                "state_after_wrong_thread": state_after_rejection,
                "terminal_state": handle.state,
                "result_supervisor_pid": result.supervisor_pid,
            },
        )

    if mode == "SECOND_BEGIN":
        second_error = ""
        try:
            runtime.begin_bounded_nested_creator_two_birth_live_prefix_v1(
                control_cgroup_fd=control_fd
            )
        except BaseException as error:
            second_error = type(error).__name__
        if not second_error:
            raise RuntimeError("second begin unexpectedly returned a live handle")
        state_after_rejection = handle.state
        result = runtime.close_bounded_nested_creator_two_birth_live_prefix_v1(
            handle
        )
        return _closed_summary(
            mode=mode,
            control_fd=control_fd,
            baseline_fd_count=baseline_fd_count,
            baseline_subreaper=baseline_subreaper,
            extra={
                **common,
                "second_begin_error_type": second_error,
                "state_after_second_begin": state_after_rejection,
                "terminal_state": handle.state,
                "result_supervisor_pid": result.supervisor_pid,
            },
        )

    raise RuntimeError(f"unknown live-prefix test mode: {mode}")


def main() -> int:
    mode = sys.argv[1] if len(sys.argv) > 1 else "BEGIN_CLOSE"
    if mode not in {
        "ABORT_QUARANTINE_RETRY",
        "AFTER_BEGIN_RECOVERY_CONTROL_CLOSE",
        "AFTER_BEGIN_RECOVERY_REGISTRY_CLEAR",
        "AFTER_CONTROL_CLOSE",
        "AFTER_PREFIX_REGISTER",
        "AFTER_REGISTRY_DELETE",
        "AFTER_SHUTDOWN_ECHO",
        "AFTER_SUPERVISOR_REAP",
        "ATFORK",
        "BEFORE_SUBREAPER_RESTORE",
        "BEGIN_CLOSE",
        "BEGIN_CLEANUP_QUARANTINE_RECOVERY",
        "BEGIN_ENTRY_FORK",
        "BEGIN_QUARANTINE_UNRELATED_CHILD_GUARD",
        "EXPLICIT_ABORT",
        "HANDLE_PRIVATE_TAMPER",
        "HIDDEN_BEGIN_CLEANUP_THREE_RECOVERIES",
        "PENDING_SIGINT_FINAL_MASK_RESTORE",
        "UNRELATED_CHILD_ABORT_GUARD",
        "WRONG_THREAD",
        "SECOND_BEGIN",
    }:
        raise RuntimeError(f"unknown live-prefix test mode: {mode}")
    scope = _current_scope_path()
    root_fd = os.open(
        scope, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW
    )
    suffix = f"{os.getpid()}-{uuid.uuid4().hex}"
    guardian_name = f"acfqp-guardian-{suffix}"
    delegated_name = f"acfqp-delegated-{suffix}"
    outer_name = f"acfqp-outer-{suffix}"
    guardian_fd = delegated_fd = outer_fd = control_fd = -1
    moved = False
    try:
        os.mkdir(guardian_name, mode=0o700, dir_fd=root_fd)
        guardian_fd = _open_dir_at(root_fd, guardian_name)
        _write_at(guardian_fd, "cgroup.procs", f"{os.getpid()}\n".encode())
        moved = True
        _write_at(root_fd, "cgroup.subtree_control", b"+memory +pids\n")
        os.mkdir(delegated_name, mode=0o700, dir_fd=root_fd)
        delegated_fd = _open_dir_at(root_fd, delegated_name)
        _write_at(delegated_fd, "cgroup.subtree_control", b"+memory +pids\n")
        os.mkdir(outer_name, mode=0o700, dir_fd=delegated_fd)
        outer_fd = _open_dir_at(delegated_fd, outer_name)
        _write_at(outer_fd, "memory.max", str(64 * 1024 * 1024).encode() + b"\n")
        _write_at(outer_fd, "pids.max", b"3\n")
        _write_at(outer_fd, "cgroup.max.depth", b"1\n")
        _write_at(outer_fd, "cgroup.max.descendants", b"1\n")
        _write_at(outer_fd, "cgroup.subtree_control", b"+memory +pids\n")
        os.mkdir("control", mode=0o700, dir_fd=outer_fd)
        control_fd = _open_dir_at(outer_fd, "control")
        _write_at(control_fd, "pids.max", b"2\n")
        print(
            json.dumps(
                _run_mode(control_fd, mode),
                sort_keys=True,
                separators=(",", ":"),
            )
        )
        return 0
    finally:
        if control_fd >= 0:
            _write_at(control_fd, "cgroup.kill", b"1\n")
            _wait_empty(control_fd)
            os.rmdir("control", dir_fd=outer_fd)
        if outer_fd >= 0:
            os.close(outer_fd)
            outer_fd = -1
            os.rmdir(outer_name, dir_fd=delegated_fd)
        if delegated_fd >= 0:
            os.close(delegated_fd)
            delegated_fd = -1
            os.rmdir(delegated_name, dir_fd=root_fd)
        if moved:
            _write_at(root_fd, "cgroup.subtree_control", b"-memory -pids\n")
            _write_at(root_fd, "cgroup.procs", f"{os.getpid()}\n".encode())
        if guardian_fd >= 0:
            _wait_empty(guardian_fd)
            os.close(guardian_fd)
            os.rmdir(guardian_name, dir_fd=root_fd)
        if control_fd >= 0:
            os.close(control_fd)
        os.close(root_fd)


if __name__ == "__main__":
    raise SystemExit(main())
