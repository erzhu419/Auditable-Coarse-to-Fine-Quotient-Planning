from __future__ import annotations

import ast
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from types import ModuleType

import pytest

from acfqp import construction_k7_standard_2048_process_supervision_v42r1 as processio
from acfqp.phase3e_ids import loads_canonical_json
from scripts import supervise_v42_standard_2048_remote_ordinal2 as supervisor


def _wait_pid_absent(pid: int, timeout: float = 5.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return True
        time.sleep(0.02)
    return False


def test_bounded_message_preserves_the_final_utf8_byte_cap() -> None:
    prefix = "x" * (processio.MAX_EXCEPTION_MESSAGE_BYTES - 2)
    bounded = processio.bounded_message(prefix + "€" * 10)
    assert bounded == prefix
    assert len(bounded.encode("utf-8")) <= processio.MAX_EXCEPTION_MESSAGE_BYTES


def test_supervisor_normal_return_codes_are_not_converted_to_70(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(supervisor, "_formal_supervisor", lambda: 0)
    assert supervisor.main(["--formal-supervisor"]) == 0
    monkeypatch.setattr(supervisor, "_formal_supervisor", lambda: 2)
    assert supervisor.main(["--formal-supervisor"]) == 2

    source = Path(supervisor.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    terminal_if = tree.body[-1]
    assert isinstance(terminal_if, ast.If)
    assert isinstance(terminal_if.body[0], ast.Try)
    guarded = terminal_if.body[0]
    assert isinstance(guarded.handlers[0].type, ast.Name)
    assert guarded.handlers[0].type.id == "Exception"
    assert isinstance(terminal_if.body[-1], ast.Raise)
    assert "SystemExit" in ast.unparse(terminal_if.body[-1])


def test_supervisor_help_system_exit_is_not_misreported_as_process_failure() -> None:
    completed = subprocess.run(
        (sys.executable, str(Path(supervisor.__file__).resolve()), "--help"),
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert completed.returncode == 0
    assert b"isolated_process_failure" not in completed.stderr


def test_frozen_authority_alias_checks_exact_file_origin_and_forbidden_origins(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delitem(sys.modules, supervisor.OLD_AUTHORITY_MODULE, raising=False)
    monkeypatch.delattr(
        supervisor.acfqp, supervisor.OLD_AUTHORITY_ATTRIBUTE, raising=False
    )
    supervisor._install_frozen_authority_alias()  # noqa: SLF001
    assert sys.modules[supervisor.OLD_AUTHORITY_MODULE] is supervisor.authority

    late_alias = ModuleType(supervisor.OLD_AUTHORITY_MODULE)
    late_alias.__file__ = str(
        supervisor.ROOT
        / "src/acfqp/construction_k7_standard_2048_execution_authority_v42.py"
    )
    monkeypatch.setitem(sys.modules, supervisor.OLD_AUTHORITY_MODULE, late_alias)
    with pytest.raises(
        supervisor.V42RemoteOrdinal2SupervisorError,
        match="alias|source origin",
    ):
        supervisor._verify_runtime_authority_alias("late fixture")  # noqa: SLF001
    monkeypatch.setitem(
        sys.modules, supervisor.OLD_AUTHORITY_MODULE, supervisor.authority
    )

    monkeypatch.setattr(supervisor.authority, "__file__", "/tmp/foreign-authority.py")
    with pytest.raises(
        supervisor.V42RemoteOrdinal2SupervisorError,
        match="origin",
    ):
        supervisor._install_frozen_authority_alias()  # noqa: SLF001

    foreign = ModuleType("acfqp.ordinal1_origin_attack")
    foreign.__file__ = str(
        supervisor.ROOT
        / "src/acfqp/construction_k7_standard_2048_execution_authority_v42.py"
    )
    sys.modules[foreign.__name__] = foreign
    try:
        with pytest.raises(
            supervisor.V42RemoteOrdinal2SupervisorError,
            match="forbidden repository source origins",
        ):
            supervisor._reject_forbidden_source_origins(  # noqa: SLF001
                supervisor.ORDINAL1_FORBIDDEN_SOURCE_ORIGINS, "fixture"
            )
    finally:
        sys.modules.pop(foreign.__name__, None)


def test_runtime_import_guard_denies_manifested_ordinal1_authority_origin() -> None:
    forbidden = (
        "src/acfqp/construction_k7_standard_2048_execution_authority_v42.py"
    )
    assert forbidden in supervisor.authority.FORMAL_REMOTE_SOURCE_ROOTS
    guard = supervisor.authority._RemoteManifestImportGuardV42r1(  # noqa: SLF001
        supervisor.ROOT, frozenset({forbidden})
    )
    with pytest.raises(Exception, match="forbidden predecessor module"):
        guard.find_spec(supervisor.OLD_AUTHORITY_MODULE)

    campaign_source = (
        supervisor.ROOT
        / "src/acfqp/construction_k7_standard_2048_fresh_terminal_campaign_v42.py"
    ).read_text(encoding="utf-8")
    formal_episode = campaign_source.split("def _run_formal_episode", 1)[1].split(
        "\n\n", 1
    )[0]
    assert formal_episode.count(
        "verify_runtime_repository_modules_in_manifest_v42"
    ) == 2


def test_capped_child_preserves_ordinary_nonzero_return_code() -> None:
    completed = processio.run_capped_child(
        role="FIXTURE",
        command=(sys.executable, "-c", "raise SystemExit(2)"),
        stdout_cap=1024,
        stderr_cap=1024,
        timeout_seconds=5,
        cwd=Path("/tmp"),
    )
    assert completed.returncode == 2
    assert completed.stdout == b""
    assert completed.stderr == b""


def test_fresh_process_group_kills_grandchild_holding_inherited_pipe() -> None:
    caller_group = os.getpgrp()
    with tempfile.TemporaryDirectory(prefix="acfqp-v42-pg-", dir="/tmp") as base:
        script = Path(base) / "child.py"
        script.write_text(
            "import os, subprocess, sys\n"
            "grandchild = subprocess.Popen([sys.executable, '-c', "
            "'import time; time.sleep(60)'])\n"
            "os.write(1, f'{os.getpid()} {grandchild.pid}\\n'.encode())\n"
            "os._exit(0)\n",
            encoding="utf-8",
        )
        with pytest.raises(processio.V42RemoteOrdinal2ChildError) as raised:
            processio.run_capped_child(
                role="PIPE_HOLDER",
                command=(sys.executable, str(script)),
                stdout_cap=1024,
                stderr_cap=1024,
                timeout_seconds=5,
                cwd=Path(base),
            )
    assert raised.value.classification == (
        "PIPE_HOLDER_DIRECT_EXIT_WITH_INHERITED_PIPE_OPEN"
    )
    assert "CONFIRMED_DIRECT_WAIT_AND_PIPE_EOF" in raised.value.group_teardown
    direct_pid, grandchild_pid = map(int, raised.value.stdout.strip().split())
    assert _wait_pid_absent(direct_pid)
    assert _wait_pid_absent(grandchild_pid)
    assert os.getpgrp() == caller_group


def test_stream_cap_uses_term_then_kill_for_ignoring_process_group() -> None:
    caller_group = os.getpgrp()
    with tempfile.TemporaryDirectory(prefix="acfqp-v42-cap-", dir="/tmp") as base:
        script = Path(base) / "ignore.py"
        script.write_text(
            "import os, signal, subprocess, sys, time\n"
            "signal.signal(signal.SIGTERM, signal.SIG_IGN)\n"
            "grandchild = subprocess.Popen([sys.executable, '-c', "
            "'import signal,time; signal.signal(signal.SIGTERM, signal.SIG_IGN); "
            "time.sleep(60)'])\n"
            "os.write(1, f'{os.getpid()} {grandchild.pid} '.encode() + b'x' * 4096)\n"
            "time.sleep(60)\n",
            encoding="utf-8",
        )
        with pytest.raises(processio.V42RemoteOrdinal2ChildError) as raised:
            processio.run_capped_child(
                role="CAP",
                command=(sys.executable, str(script)),
                stdout_cap=128,
                stderr_cap=1024,
                timeout_seconds=5,
                cwd=Path(base),
            )
    assert raised.value.classification == "CAP_STDOUT_CAP_EXCEEDED"
    assert raised.value.group_teardown.startswith("TERM_THEN_KILL_GROUP_CONFIRMED")
    direct_pid, grandchild_pid = map(int, raised.value.stdout.split(maxsplit=2)[:2])
    assert _wait_pid_absent(direct_pid)
    assert _wait_pid_absent(grandchild_pid)
    assert os.getpgrp() == caller_group


def test_typed_failure_retains_nested_group_teardown(
    capsysbinary: pytest.CaptureFixture[bytes],
) -> None:
    error = processio.V42RemoteOrdinal2ChildError(
        "fixture",
        role="PRODUCER",
        returncode=-9,
        stdout=b"",
        stderr=b"",
        classification="PRODUCER_TIMEOUT",
        group_teardown="TERM_THEN_KILL_GROUP_CONFIRMED_DIRECT_WAIT_AND_PIPE_EOF",
    )
    supervisor._emit_typed_process_failure(error)  # noqa: SLF001
    raw = capsysbinary.readouterr().err
    document = loads_canonical_json(raw[:-1])
    assert document["failure_classification"] == "PRODUCER_TIMEOUT"
    assert document["nested_group_teardown"].endswith(
        "CONFIRMED_DIRECT_WAIT_AND_PIPE_EOF"
    )


def test_nested_roles_inherit_the_one_top_level_formal_process_group() -> None:
    source = Path(supervisor.__file__).read_text(encoding="utf-8")
    assert source.count("start_new_session=False") == 2
    assert "os.getpid() != os.getpgrp()" in source
    assert "os.getpid() != os.getsid(0)" in source
