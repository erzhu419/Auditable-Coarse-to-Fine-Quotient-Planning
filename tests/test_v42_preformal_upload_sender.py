from __future__ import annotations

from dataclasses import replace
import hashlib
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
from typing import Any

import pytest

from acfqp import construction_k7_standard_2048_materialization_transport_v42r1 as transport
from acfqp.phase3e_ids import canonical_json_bytes
from scripts import publish_v42_preformal_upload_journal as journal
from scripts import run_v42_preformal_upload_sender as sender
from tests.test_construction_k7_standard_2048_materialization_transport_v42r1 import (
    _attempt,
    _context,
    _fixture,
    _plan,
    _receipt,
    _receiver_wire,
    _token,
)


def _observation(
    *,
    stdout: bytes,
    returncode: int = 0,
    expected_input: int = 17,
    stderr: bytes = b"",
) -> sender._ChildObservation:  # noqa: SLF001
    return sender._ChildObservation(  # noqa: SLF001
        exec_succeeded=True,
        returncode=returncode,
        timed_out=False,
        stdin_expected_byte_count=expected_input,
        stdin_sent_byte_count=expected_input,
        stdin_complete=True,
        stdout_raw=stdout,
        stdout_total_byte_count=len(stdout),
        stdout_sha256=hashlib.sha256(stdout).hexdigest(),
        stdout_overflow=False,
        stdout_eof=True,
        stderr_prefix=stderr,
        stderr_total_byte_count=len(stderr),
        stderr_sha256=hashlib.sha256(stderr).hexdigest(),
        stderr_overflow=False,
        stderr_eof=True,
    )


def test_sender_segments_are_the_exact_receiver_wire_without_archive_copy() -> None:
    plan = _plan()
    attempt = _attempt(plan)
    (
        normalized_plan,
        normalized_attempt,
        header,
        controls,
        _loader_raw,
        receiver_raw,
        _chain,
    ) = sender._normalized_sender_inputs(  # noqa: SLF001
        plan=plan,
        attempt=attempt,
        predecessor_chain=None,
        **_context(),
    )
    segments = sender._outbound_segments_v42r1(  # noqa: SLF001
        plan=normalized_plan,
        attempt=normalized_attempt,
        header=header,
        controls=controls,
        receiver_source_raw=receiver_raw,
    )
    _expected_header, expected_wire = _receiver_wire(plan=plan, attempt=attempt)

    assert segments[0] is receiver_raw
    assert segments[-1] is controls[transport.PREFORMAL_STREAM_FRAME_ORDER[-1]]
    assert b"".join(segments[1:]) == expected_wire


def test_held_network_boundary_keeps_snapshot_open_through_marker(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with tempfile.TemporaryDirectory(
        prefix="acfqp-v42-held-network-boundary-", dir="/tmp"
    ) as base:
        monkeypatch.setattr(transport, "LOCAL_TRANSPORT_PARENT", Path(base))
        plan = _plan(token=_token("held-boundary"))
        attempt = _attempt(plan)
        journal.publish_pre_network_journal_v42r1(
            plan=plan, attempt=attempt, **_context()
        )
        boundary = journal.hold_network_start_boundary_v42r1(
            plan=plan, attempt=attempt, **_context()
        )
        snapshot_fd = boundary._snapshot.current_slot.directory.descriptor  # noqa: SLF001
        with boundary:
            boundary.verify_exact(durable=True)
            assert not Path(plan["local_network_start_path"]).exists()
            start = boundary.publish_once()
            assert start["preformal_upload_plan_id"] == plan[
                "preformal_upload_plan_id"
            ]
            assert boundary.marker_effect_may_have_started is True
            assert boundary.marker_published is True
            assert Path(plan["local_network_start_path"]).exists()
            os.fstat(snapshot_fd)
            boundary.verify_exact(durable=True)
        with pytest.raises(OSError):
            os.fstat(snapshot_fd)


def test_held_boundary_marks_irreversible_edge_before_marker_write(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with tempfile.TemporaryDirectory(
        prefix="acfqp-v42-held-marker-failure-", dir="/tmp"
    ) as base:
        monkeypatch.setattr(transport, "LOCAL_TRANSPORT_PARENT", Path(base))
        plan = _plan(token=_token("held-marker-failure"))
        attempt = _attempt(plan)
        journal.publish_pre_network_journal_v42r1(
            plan=plan, attempt=attempt, **_context()
        )
        boundary = journal.hold_network_start_boundary_v42r1(
            plan=plan, attempt=attempt, **_context()
        )

        def reject_marker(*_args: Any, **_kwargs: Any) -> Any:
            raise OSError("injected marker write failure")

        monkeypatch.setattr(journal, "_write_once_at", reject_marker)
        with boundary:
            with pytest.raises(OSError, match="marker write failure"):
                boundary.publish_once()
            assert boundary.marker_effect_may_have_started is True
            assert boundary.marker_published is False


def test_descriptor_exec_pump_drains_stderr_while_streaming_stdin() -> None:
    root = Path(__file__).resolve().parents[1]
    probe = """
import os
from acfqp import construction_k7_standard_2048_materialization_transport_v42r1 as transport
from scripts import run_v42_preformal_upload_sender as sender

before = len(os.listdir('/proc/self/fd'))
executable_fd = os.open('/usr/bin/python3', os.O_RDONLY | os.O_CLOEXEC)
raw = b'sender-pipe-payload-' * 20000
code = (
    "import os,sys;"
    "os.write(2,b'e'*200000);"
    "data=sys.stdin.buffer.read();"
    "sys.stdout.buffer.write(data[::-1])"
)
prepared = sender._prepare_pinned_child(
    executable_fd=executable_fd,
    argv=('/usr/bin/python3', '-I', '-S', '-B', '-c', code),
    environment=dict(transport.LOCAL_DISPATCH_ENVIRONMENT),
    segments=(raw[:12345], raw[12345:]),
    stdout_cap=1024 * 1024,
    stderr_cap=64 * 1024,
    timeout_seconds=10.0,
)
try:
    observation = prepared.spawn_and_pump()
finally:
    prepared.close()
    os.close(executable_fd)
after = len(os.listdir('/proc/self/fd'))
assert after == before
assert observation.exec_succeeded is True
assert observation.returncode == 0
assert observation.timed_out is False
assert observation.stdin_complete is True
assert observation.stdout_raw == raw[::-1]
assert observation.stdout_eof is True
assert observation.stderr_total_byte_count == 200000
assert len(observation.stderr_prefix) == 64 * 1024
assert observation.stderr_overflow is True
assert observation.stderr_eof is True
"""
    completed = subprocess.run(
        [sys.executable, "-c", probe],
        cwd=root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr.decode(errors="replace")
    assert completed.stdout == b""
    assert completed.stderr == b""


def test_descriptor_exec_closes_audit_hook_fd_opened_at_fork() -> None:
    root = Path(__file__).resolve().parents[1]
    probe = r"""
import fcntl
import os
import sys
from acfqp import construction_k7_standard_2048_materialization_transport_v42r1 as transport
from scripts import run_v42_preformal_upload_sender as sender

injected = []
def audit_hook(event, _arguments):
    if event == "os.fork" and not injected:
        injected.append(-1)
        descriptor = os.open("/dev/null", os.O_RDONLY)
        os.set_inheritable(descriptor, True)
        injected[0] = descriptor

sys.addaudithook(audit_hook)
executable_fd = os.open("/usr/bin/python3", os.O_RDONLY | os.O_CLOEXEC)
code = r'''
import fcntl, os, sys
live = []
for name in os.listdir("/proc/self/fd"):
    try:
        descriptor = int(name)
        fcntl.fcntl(descriptor, fcntl.F_GETFD)
    except (ValueError, OSError):
        continue
    live.append(descriptor)
if sorted(live) != [0, 1, 2]:
    sys.exit(91)
sys.stdout.buffer.write(b"EXACT_012")
'''
prepared = sender._prepare_pinned_child(
    executable_fd=executable_fd,
    argv=("/usr/bin/python3", "-I", "-S", "-B", "-c", code),
    environment=dict(transport.LOCAL_DISPATCH_ENVIRONMENT),
    segments=(),
    stdout_cap=1024,
    stderr_cap=1024,
    timeout_seconds=10.0,
)
try:
    observation = prepared.spawn_and_pump()
finally:
    prepared.close()
    os.close(executable_fd)
    if injected and injected[0] >= 0:
        os.close(injected[0])
assert observation.exec_succeeded is True
assert observation.returncode == 0
assert observation.stdout_raw == b"EXACT_012"
assert observation.stdout_eof and observation.stderr_eof
"""
    completed = subprocess.run(
        [sys.executable, "-c", probe],
        cwd=root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr.decode(errors="replace")
    assert completed.stdout == b""


def test_preexisting_python_trace_hook_is_rejected_before_child_preparation() -> None:
    root = Path(__file__).resolve().parents[1]
    probe = r'''
import os
import sys
from acfqp import construction_k7_standard_2048_materialization_transport_v42r1 as transport
from scripts import run_v42_preformal_upload_sender as sender

before = len(os.listdir("/proc/self/fd"))
executable_fd = os.open("/usr/bin/python3", os.O_RDONLY | os.O_CLOEXEC)
def tracer(_frame, _event, _argument):
    return tracer
sys.settrace(tracer)
try:
    try:
        sender._prepare_pinned_child(
            executable_fd=executable_fd,
            argv=("/usr/bin/python3", "-I", "-S", "-B", "-c", "pass"),
            environment=dict(transport.LOCAL_DISPATCH_ENVIRONMENT),
            segments=(),
            stdout_cap=1024,
            stderr_cap=1024,
            timeout_seconds=10.0,
        )
    except sender.V42PreformalSenderError as error:
        assert "trace and profile hooks" in str(error)
    else:
        raise AssertionError("trace hook was not rejected")
finally:
    sys.settrace(None)
    os.close(executable_fd)
after = len(os.listdir("/proc/self/fd"))
assert after == before, (before, after)
'''
    completed = subprocess.run(
        [sys.executable, "-c", probe],
        cwd=root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr.decode(errors="replace")
    assert completed.stdout == b""


def test_child_clears_trace_hook_installed_by_the_fork_audit_event() -> None:
    root = Path(__file__).resolve().parents[1]
    probe = r"""
import fcntl
import linecache
import os
import sys
from acfqp import construction_k7_standard_2048_materialization_transport_v42r1 as transport
from scripts import run_v42_preformal_upload_sender as sender

origin_pid = os.getpid()
installed = []
opened = []
def tracer(frame, event, _argument):
    if os.getpid() != origin_pid and event == "line" and not opened:
        source = linecache.getline(frame.f_code.co_filename, frame.f_lineno)
        if "signal.pthread_sigmask(signal.SIG_SETMASK, set())" in source:
            descriptor = os.open("/dev/null", os.O_RDONLY)
            os.set_inheritable(descriptor, True)
            opened.append(descriptor)
    return tracer
def audit_hook(event, _arguments):
    if event == "os.fork" and not installed:
        installed.append(True)
        frame = sys._getframe()
        while frame is not None:
            frame.f_trace = tracer
            frame = frame.f_back
        sys.settrace(tracer)

sys.addaudithook(audit_hook)
executable_fd = os.open("/usr/bin/python3", os.O_RDONLY | os.O_CLOEXEC)
code = r'''
import fcntl, os, sys
live = []
for name in os.listdir("/proc/self/fd"):
    try:
        descriptor = int(name)
        fcntl.fcntl(descriptor, fcntl.F_GETFD)
    except (ValueError, OSError):
        continue
    live.append(descriptor)
if sorted(live) != [0, 1, 2]:
    sys.exit(92)
sys.stdout.buffer.write(b"TRACE_CLEARED_EXACT_012")
'''
prepared = sender._prepare_pinned_child(
    executable_fd=executable_fd,
    argv=("/usr/bin/python3", "-I", "-S", "-B", "-c", code),
    environment=dict(transport.LOCAL_DISPATCH_ENVIRONMENT),
    segments=(),
    stdout_cap=1024,
    stderr_cap=1024,
    timeout_seconds=10.0,
)
try:
    observation = prepared.spawn_and_pump()
finally:
    sys.settrace(None)
    prepared.close()
    os.close(executable_fd)
assert observation.exec_succeeded is True
assert observation.returncode == 0
assert observation.stdout_raw == b"TRACE_CLEARED_EXACT_012"
assert observation.stdout_eof and observation.stderr_eof
"""
    completed = subprocess.run(
        [sys.executable, "-c", probe],
        cwd=root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr.decode(errors="replace")
    assert completed.stdout == b""


def test_sigpipe_default_cannot_kill_parent_pump_and_is_restored() -> None:
    root = Path(__file__).resolve().parents[1]
    probe = r'''
import os
import signal
from acfqp import construction_k7_standard_2048_materialization_transport_v42r1 as transport
from scripts import run_v42_preformal_upload_sender as sender

signal.signal(signal.SIGPIPE, signal.SIG_DFL)
executable_fd = os.open("/usr/bin/python3", os.O_RDONLY | os.O_CLOEXEC)
code = "import os; os.close(0)"
prepared = sender._prepare_pinned_child(
    executable_fd=executable_fd,
    argv=("/usr/bin/python3", "-I", "-S", "-B", "-c", code),
    environment=dict(transport.LOCAL_DISPATCH_ENVIRONMENT),
    segments=(b"x" * (2 * 1024 * 1024),),
    stdout_cap=1024,
    stderr_cap=1024,
    timeout_seconds=10.0,
)
try:
    observation = prepared.spawn_and_pump()
finally:
    prepared.close()
    os.close(executable_fd)
assert observation.returncode == 0
assert observation.stdin_complete is False
assert signal.getsignal(signal.SIGPIPE) is signal.SIG_DFL
'''
    completed = subprocess.run(
        [sys.executable, "-c", probe],
        cwd=root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr.decode(errors="replace")
    assert completed.stdout == b""


def test_continuous_stdout_cannot_postpone_the_child_deadline() -> None:
    root = Path(__file__).resolve().parents[1]
    probe = r'''
import os
import signal
import time
from scripts import run_v42_preformal_upload_sender as sender

stdin_read, stdin_write = os.pipe2(os.O_CLOEXEC)
stdout_read, stdout_write = os.pipe2(os.O_CLOEXEC)
stderr_read, stderr_write = os.pipe2(os.O_CLOEXEC)
pid = os.fork()
if pid == 0:
    os.close(stdin_read); os.close(stdin_write); os.close(stdout_read)
    os.close(stderr_read)
    try:
        while True:
            os.write(stdout_write, b"z" * 4096)
    except BaseException:
        os._exit(0)
os.close(stdin_read); os.close(stdout_write); os.close(stderr_write)

original_read = sender.os.read
original_kill = sender._kill_noexcept
state = {"synthetic_reads": 0, "pump_killed": False, "self_killed": False}
def bounded_slow_read(descriptor, byte_count):
    if (
        descriptor == stdout_read
        and not state["pump_killed"]
        and not state["self_killed"]
    ):
        state["synthetic_reads"] += 1
        time.sleep(0.003)
        if state["synthetic_reads"] >= 100:
            state["self_killed"] = True
            original_kill(pid)
        return b"x"
    return original_read(descriptor, byte_count)
def observed_kill(child_pid):
    state["pump_killed"] = True
    original_kill(child_pid)
sender.os.read = bounded_slow_read
sender._kill_noexcept = observed_kill
started = time.monotonic()
observation = sender._pump_child_process(
    pid=pid,
    stdin_fd=stdin_write,
    stdout_fd=stdout_read,
    stderr_fd=stderr_read,
    segments=(),
    expected_input_byte_count=0,
    stdout_cap=1024,
    stderr_cap=1024,
    deadline=started + 0.03,
    exec_succeeded=False,
    already_timed_out=False,
)
elapsed = time.monotonic() - started
assert state["pump_killed"] is True
assert state["self_killed"] is False
assert state["synthetic_reads"] < 30
assert observation.timed_out is True
assert observation.returncode == -signal.SIGKILL
assert elapsed < 0.15, elapsed
'''
    completed = subprocess.run(
        [sys.executable, "-c", probe],
        cwd=root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr.decode(errors="replace")
    assert completed.stdout == b""


def test_parent_exception_after_fork_owns_and_reaps_the_child() -> None:
    root = Path(__file__).resolve().parents[1]
    probe = r'''
import os
from acfqp import construction_k7_standard_2048_materialization_transport_v42r1 as transport
from scripts import run_v42_preformal_upload_sender as sender

before = len(os.listdir("/proc/self/fd"))
executable_fd = os.open("/usr/bin/python3", os.O_RDONLY | os.O_CLOEXEC)
prepared = sender._prepare_pinned_child(
    executable_fd=executable_fd,
    argv=(
        "/usr/bin/python3", "-I", "-S", "-B", "-c",
        "import time; time.sleep(30)",
    ),
    environment=dict(transport.LOCAL_DISPATCH_ENVIRONMENT),
    segments=(),
    stdout_cap=1024,
    stderr_cap=1024,
    timeout_seconds=10.0,
)
original_close = sender._close_noexcept
original_fork = sender.os.fork
state = {"close_calls": 0, "child_pid": None}
def one_parent_interrupt(descriptor):
    state["close_calls"] += 1
    if state["close_calls"] == 1:
        raise KeyboardInterrupt("injected parent endpoint close interruption")
    original_close(descriptor)
def recording_fork():
    child_pid = original_fork()
    if child_pid > 0:
        state["child_pid"] = child_pid
    return child_pid
sender._close_noexcept = one_parent_interrupt
sender.os.fork = recording_fork
try:
    try:
        prepared.spawn_and_pump()
    except KeyboardInterrupt as error:
        assert "endpoint close" in str(error)
    else:
        raise AssertionError("injected parent exception was not observed")
finally:
    prepared.close()
    os.close(executable_fd)
assert state["child_pid"] is not None
try:
    os.waitpid(state["child_pid"], os.WNOHANG)
except ChildProcessError:
    pass
else:
    raise AssertionError("forked child was not reaped")
after = len(os.listdir("/proc/self/fd"))
assert after == before, (before, after)
'''
    completed = subprocess.run(
        [sys.executable, "-c", probe],
        cwd=root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr.decode(errors="replace")
    assert completed.stdout == b""


def test_complete_classifier_requires_every_exact_output_condition() -> None:
    plan = _plan()
    attempt = _attempt(plan)
    controls, loader_raw, receiver_raw = _fixture()
    receipt = _receipt(plan, attempt)
    receipt_raw = canonical_json_bytes(receipt)
    valid = _observation(stdout=receipt_raw, stderr=b"diagnostic only")
    arguments = {
        "plan": plan,
        "attempt": attempt,
        "controls": controls,
        "loader_source_raw": loader_raw,
        "receiver_source_raw": receiver_raw,
        "predecessor_chain": [],
    }
    assert sender._complete_receipt_from_observation(  # noqa: SLF001
        observation=valid, **arguments
    ) == receipt

    invalid = (
        replace(valid, returncode=1),
        replace(
            valid,
            stdout_raw=receipt_raw + b"\n",
            stdout_total_byte_count=len(receipt_raw) + 1,
            stdout_sha256=hashlib.sha256(receipt_raw + b"\n").hexdigest(),
        ),
        replace(valid, stdout_overflow=True),
        replace(valid, stdout_eof=False),
        replace(valid, stdin_complete=False),
        replace(valid, timed_out=True),
        replace(valid, exec_succeeded=False),
        replace(valid, stderr_eof=False),
    )
    for observation in invalid:
        assert sender._complete_receipt_from_observation(  # noqa: SLF001
            observation=observation, **arguments
        ) is None


class _FakeSSH:
    descriptor = 99


class _FakePins:
    ssh = _FakeSSH()

    def verify(self) -> None:
        return None

    def close(self) -> None:
        return None


class _FakePrepared:
    def __init__(self, observation: sender._ChildObservation) -> None:  # noqa: SLF001
        self.observation = observation

    def verify_prepared(self) -> None:
        return None

    def spawn_and_pump(self) -> sender._ChildObservation:  # noqa: SLF001
        return self.observation

    def close(self) -> None:
        return None


def test_sender_closes_live_tcb_rejection_as_local_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with tempfile.TemporaryDirectory(
        prefix="acfqp-v42-sender-local-failure-", dir="/tmp"
    ) as base:
        monkeypatch.setattr(transport, "LOCAL_TRANSPORT_PARENT", Path(base))
        plan = _plan(token=_token("sender-local-failure"))
        attempt = _attempt(plan)

        def reject_tcb(_plan: dict[str, Any]) -> Any:
            raise sender.V42PreformalSenderError("injected live TCB rejection")

        monkeypatch.setattr(sender, "_open_local_dispatch_pins_v42r1", reject_tcb)
        result = sender.execute_preformal_upload_v42r1(
            plan=plan, attempt=attempt, **_context()
        )

        assert result.network_start is None
        assert result.receipt is None
        assert result.diagnostic_code == "LOCAL_PRE_NETWORK_FAILURE"
        assert result.outcome["outcome_class"] == (
            transport.PREFORMAL_OUTCOME_ABANDONED_FAILURE
        )
        assert not Path(plan["local_network_start_path"]).exists()
        assert Path(plan["local_outcome_path"]).exists()
        recovered = sender.execute_preformal_upload_v42r1(
            plan=plan, attempt=attempt, **_context()
        )
        assert recovered.diagnostic_code == "RECOVERED_TERMINAL_JOURNAL"
        assert recovered.outcome == result.outcome
        assert recovered.network_start is None


@pytest.mark.parametrize("returncode,expected_complete", [(0, True), (1, False)])
def test_sender_publishes_complete_only_for_exit_zero_exact_receipt(
    monkeypatch: pytest.MonkeyPatch,
    returncode: int,
    expected_complete: bool,
) -> None:
    with tempfile.TemporaryDirectory(
        prefix="acfqp-v42-sender-classification-", dir="/tmp"
    ) as base:
        monkeypatch.setattr(transport, "LOCAL_TRANSPORT_PARENT", Path(base))
        label = f"sender-classification-{returncode}"
        plan = _plan(token=_token(label))
        attempt = _attempt(plan)
        receipt = _receipt(plan, attempt)
        receipt_raw = canonical_json_bytes(receipt)

        monkeypatch.setattr(
            sender,
            "_open_local_dispatch_pins_v42r1",
            lambda _plan: _FakePins(),
        )
        monkeypatch.setattr(
            sender,
            "_derive_identity_fingerprint_v42r1",
            lambda **_kwargs: plan["ssh_client_contract"][
                "identity_public_fingerprint"
            ],
        )

        def fake_prepare(**kwargs: Any) -> _FakePrepared:
            expected_input = sum(len(part) for part in kwargs["segments"])
            return _FakePrepared(
                _observation(
                    stdout=receipt_raw,
                    returncode=returncode,
                    expected_input=expected_input,
                    stderr=b"bounded diagnostic",
                )
            )

        monkeypatch.setattr(sender, "_prepare_pinned_child", fake_prepare)
        # This is a pure fake-child classification test; pytest's numerical
        # stack owns background worker threads, while the real fork boundary is
        # covered in isolated single-threaded subprocesses above.
        monkeypatch.setattr(sender, "_assert_single_threaded", lambda: None)
        result = sender.execute_preformal_upload_v42r1(
            plan=plan, attempt=attempt, **_context()
        )

        assert result.network_start is not None
        assert Path(plan["local_network_start_path"]).exists()
        assert result.receipt == (receipt if expected_complete else None)
        assert result.outcome["outcome_class"] == (
            transport.PREFORMAL_OUTCOME_COMPLETE
            if expected_complete
            else transport.PREFORMAL_OUTCOME_ABANDONED_AMBIGUOUS
        )
        assert Path(plan["local_receipt_path"]).exists() is expected_complete
        assert Path(plan["local_outcome_path"]).exists()


def test_sender_reentry_never_resends_an_unresolved_network_marker(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with tempfile.TemporaryDirectory(
        prefix="acfqp-v42-sender-marker-recovery-", dir="/tmp"
    ) as base:
        monkeypatch.setattr(transport, "LOCAL_TRANSPORT_PARENT", Path(base))
        plan = _plan(token=_token("sender-marker-recovery"))
        attempt = _attempt(plan)
        journal.publish_pre_network_journal_v42r1(
            plan=plan, attempt=attempt, **_context()
        )
        journal.publish_network_start_v42r1(
            plan=plan, attempt=attempt, **_context()
        )

        def forbid_dispatch(_plan: dict[str, Any]) -> Any:
            raise AssertionError("marker recovery must not reach SSH dispatch")

        monkeypatch.setattr(
            sender, "_open_local_dispatch_pins_v42r1", forbid_dispatch
        )
        result = sender.execute_preformal_upload_v42r1(
            plan=plan, attempt=attempt, **_context()
        )
        assert result.diagnostic_code == "RECOVERED_POSTNETWORK_AS_AMBIGUOUS"
        assert result.receipt is None
        assert result.outcome["outcome_class"] == (
            transport.PREFORMAL_OUTCOME_ABANDONED_AMBIGUOUS
        )
        terminal = sender.execute_preformal_upload_v42r1(
            plan=plan, attempt=attempt, **_context()
        )
        assert terminal.diagnostic_code == "RECOVERED_TERMINAL_JOURNAL"
        assert terminal.outcome == result.outcome


def test_sender_reentry_finishes_durable_receipt_before_complete_outcome(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with tempfile.TemporaryDirectory(
        prefix="acfqp-v42-sender-receipt-recovery-", dir="/tmp"
    ) as base:
        monkeypatch.setattr(transport, "LOCAL_TRANSPORT_PARENT", Path(base))
        plan = _plan(token=_token("sender-receipt-recovery"))
        attempt = _attempt(plan)
        receipt = _receipt(plan, attempt)
        outcome = transport.build_preformal_upload_outcome_v42r1(
            plan=plan,
            attempt=attempt,
            outcome_class=transport.PREFORMAL_OUTCOME_COMPLETE,
            receipt=receipt,
            **_context(),
        )
        journal.publish_pre_network_journal_v42r1(
            plan=plan, attempt=attempt, **_context()
        )
        journal.publish_network_start_v42r1(
            plan=plan, attempt=attempt, **_context()
        )
        original_write = journal._write_once_at  # noqa: SLF001

        def stop_after_receipt(
            directory_fd: int,
            name: str,
            raw: bytes,
            *,
            label: str,
        ) -> Any:
            if name == transport.PREFORMAL_OUTCOME_NAME:
                raise OSError("injected crash after durable receipt")
            return original_write(directory_fd, name, raw, label=label)

        monkeypatch.setattr(journal, "_write_once_at", stop_after_receipt)
        with pytest.raises(OSError, match="after durable receipt"):
            journal.publish_outcome_v42r1(
                plan=plan,
                attempt=attempt,
                outcome=outcome,
                receipt=receipt,
                **_context(),
            )
        assert Path(plan["local_receipt_path"]).exists()
        assert not Path(plan["local_outcome_path"]).exists()
        monkeypatch.setattr(journal, "_write_once_at", original_write)
        monkeypatch.setattr(
            sender,
            "_open_local_dispatch_pins_v42r1",
            lambda _plan: (_ for _ in ()).throw(
                AssertionError("receipt recovery must not reach SSH dispatch")
            ),
        )

        recovered = sender.execute_preformal_upload_v42r1(
            plan=plan, attempt=attempt, **_context()
        )
        assert recovered.diagnostic_code == "RECOVERED_COMPLETE_RECEIPT"
        assert recovered.receipt == receipt
        assert recovered.outcome == outcome
        assert Path(plan["local_outcome_path"]).exists()


@pytest.mark.parametrize(
    "marker_present,outcome_class,reason",
    [
        (
            True,
            transport.PREFORMAL_OUTCOME_ABANDONED_FAILURE,
            transport.PREFORMAL_ABANDONMENT_REASON_LOCAL,
        ),
        (
            False,
            transport.PREFORMAL_OUTCOME_ABANDONED_AMBIGUOUS,
            transport.PREFORMAL_ABANDONMENT_REASON_AMBIGUOUS,
        ),
    ],
)
def test_recovery_rejects_outcome_whose_class_disagrees_with_marker_inventory(
    monkeypatch: pytest.MonkeyPatch,
    marker_present: bool,
    outcome_class: str,
    reason: str,
) -> None:
    with tempfile.TemporaryDirectory(
        prefix="acfqp-v42-recovery-semantic-inventory-", dir="/tmp"
    ) as base:
        monkeypatch.setattr(transport, "LOCAL_TRANSPORT_PARENT", Path(base))
        plan = _plan(token=_token(f"semantic-{marker_present}-{outcome_class}"))
        attempt = _attempt(plan)
        journal.publish_pre_network_journal_v42r1(
            plan=plan, attempt=attempt, **_context()
        )
        if marker_present:
            journal.publish_network_start_v42r1(
                plan=plan, attempt=attempt, **_context()
            )
        outcome = transport.build_preformal_upload_outcome_v42r1(
            plan=plan,
            attempt=attempt,
            outcome_class=outcome_class,
            receipt=None,
            abandonment_reason_code=reason,
            **_context(),
        )
        raw = canonical_json_bytes(outcome)
        outcome_fd = os.open(
            plan["local_outcome_path"],
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC,
            0o400,
        )
        try:
            offset = 0
            while offset < len(raw):
                offset += os.write(outcome_fd, raw[offset:])
            os.fsync(outcome_fd)
        finally:
            os.close(outcome_fd)
        slot_fd = os.open(plan["local_ordinal_slot"], os.O_RDONLY | os.O_CLOEXEC)
        try:
            os.fsync(slot_fd)
        finally:
            os.close(slot_fd)

        with pytest.raises(
            journal.V42PreformalJournalError,
            match="outcome disagrees with marker/receipt inventory",
        ):
            journal.inspect_preformal_upload_journal_v42r1(
                plan=plan, attempt=attempt, **_context()
            )
