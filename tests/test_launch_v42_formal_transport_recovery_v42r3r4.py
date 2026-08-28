from __future__ import annotations

import ast
import hashlib
import json
import os
from pathlib import Path
import shlex
import stat
import time
from types import SimpleNamespace

import pytest

from scripts import launch_v42_formal_transport_recovery_v42r3r4 as launcher


@pytest.fixture(autouse=True)
def _sealed_test_harness(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(launcher, "_EARLY_SEALED_MATERIALS_VERIFIED", True)
    monkeypatch.setattr(launcher, "_AUTHENTICATED_STAGE_SELF_RAW", b"stage1")
    monkeypatch.setattr(launcher, "_AUTHENTICATED_BOOTSTRAP_RAW", b"stage0")


def test_recovery_launcher_exposes_no_effect_capable_mode() -> None:
    parser = launcher._parser()  # noqa: SLF001
    help_text = parser.format_help()
    assert "--verify-inputs-only" in help_text
    assert "--inspect-retained-launch-v42r3r4" in help_text
    for forbidden in (
        "--probe-host", "--prepare-once", "--admit-launch",
        "--service", "--scientific-launch",
    ):
        assert forbidden not in help_text
    source = Path(launcher.__file__).read_text(encoding="utf-8")
    assert "/usr/bin/systemd-run" not in source
    assert "systemctl start" not in source
    assert "systemctl stop" not in source
    assert "reset-failed" not in source


def test_launcher_imports_no_project_module_before_authentication() -> None:
    tree = ast.parse(Path(launcher.__file__).read_text(encoding="utf-8"))
    imports: list[str] = []
    for node in tree.body:
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imports.append(node.module)
    assert all(
        name not in {"acfqp", "scripts"}
        and not name.startswith(("acfqp.", "scripts."))
        for name in imports
    )


def test_recovery_root_is_distinct_and_retained_root_is_frozen() -> None:
    assert launcher.RECOVERY_LOCAL_ROOT != launcher.RETAINED_LOCAL_ROOT
    assert "recovery-v42r3r4" in launcher.RECOVERY_LOCAL_ROOT.name
    assert launcher.RETAINED_LOCAL_ROOT.name.endswith("v42r3r3")
    assert launcher.RETAINED_REMOTE_ROOT.endswith("v42r3r3")


def test_recovery_journal_is_anchored_mode400_and_one_shot(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    root = tmp_path / ".recovery-v42r3r4"
    monkeypatch.setattr(launcher, "RECOVERY_LOCAL_ROOT", root)
    with launcher._RecoveryJournal.open_or_create() as journal:  # noqa: SLF001
        journal.publish_once("ATTEMPT.00000001.json", b"{}")
        assert journal.read("ATTEMPT.00000001.json") == b"{}"
        with pytest.raises(
            launcher.V42FormalTransportRecoveryLauncherError,
            match="already exists",
        ):
            journal.publish_once("ATTEMPT.00000001.json", b"{}")
    anchor = tmp_path / ("." + root.name + ".ROOT_IDENTITY.json")
    assert stat.S_IMODE(root.stat().st_mode) == 0o700
    assert stat.S_IMODE(anchor.stat().st_mode) == 0o400
    assert stat.S_IMODE((root / "ATTEMPT.00000001.json").stat().st_mode) == 0o400


def test_remote_command_binds_exact_receiver_and_ingress() -> None:
    receiver = b"raise SystemExit(0)\n"
    ingress = b'{"canonical":true}'
    recovery_plan_id = "a" * 64
    command = launcher._remote_command(  # noqa: SLF001
        receiver, ingress, recovery_plan_id=recovery_plan_id
    )
    args = shlex.split(command.removeprefix("builtin exec -c "))
    assert args[:7] == [
        "/usr/bin/python3", "-I", "-S", "-B", "-c",
        receiver.decode(), launcher.REMOTE_MODE,
    ]
    assert args[7:] == [
        hashlib.sha256(receiver).hexdigest(), str(len(receiver)),
        hashlib.sha256(ingress).hexdigest(), str(len(ingress)),
        recovery_plan_id,
    ]
    projection = launcher._actual_remote_command_projection(  # noqa: SLF001
        receiver, ingress, recovery_plan_id=recovery_plan_id
    )
    assert projection["ordered_remote_python_argv_semantics"][-1] == {
        "recovery_plan_id": recovery_plan_id
    }
    assert projection["remote_endpoint_host"] == launcher.REMOTE_ENDPOINT_HOST


def test_preexisting_unanchored_recovery_root_is_never_blessed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    root = tmp_path / ".recovery-v42r3r4"
    root.mkdir(mode=0o700)
    monkeypatch.setattr(launcher, "RECOVERY_LOCAL_ROOT", root)
    with pytest.raises(
        launcher.V42FormalTransportRecoveryLauncherError,
        match="lacks its exact identity anchor",
    ):
        launcher._RecoveryJournal.open_or_create()  # noqa: SLF001
    assert not (tmp_path / ("." + root.name + ".ROOT_IDENTITY.json")).exists()


def test_pinned_recovery_root_rejects_named_directory_replacement(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    root = tmp_path / ".recovery-v42r3r4"
    monkeypatch.setattr(launcher, "RECOVERY_LOCAL_ROOT", root)
    with launcher._RecoveryJournal.open_or_create() as journal:  # noqa: SLF001
        moved = tmp_path / ".moved-recovery-v42r3r4"
        root.rename(moved)
        root.mkdir(mode=0o700)
        with pytest.raises(
            launcher.V42FormalTransportRecoveryLauncherError,
            match="named binding changed",
        ):
            journal.verify_root()


def test_ssh_argv_is_noninteractive_and_forwarding_free() -> None:
    argv = launcher._ssh_argv(  # noqa: SLF001
        known_hosts_proc_path="/proc/self/fd/8",
        identity_proc_path="/proc/self/fd/9",
        remote_command="builtin exec -c true",
    )
    joined = "\n".join(argv)
    assert "-oBatchMode=yes" in argv
    assert "-oStrictHostKeyChecking=yes" in argv
    assert "-oClearAllForwardings=yes" in argv
    assert "-oPasswordAuthentication=no" in argv
    assert "-oRequestTTY=no" in argv
    assert "-oControlMaster=no" in argv
    assert "ProxyCommand=none" in joined
    assert argv[-2] == launcher.REMOTE_ENDPOINT_HOST
    assert argv[-1] == "builtin exec -c true"


def test_child_fact_binds_stdin_and_all_stream_facts() -> None:
    empty = hashlib.sha256(b"").hexdigest()
    observation = launcher._ChildObservation(  # noqa: SLF001
        exec_succeeded=True,
        returncode=0,
        timed_out=False,
        stdin_expected_byte_count=3,
        stdin_sent_byte_count=3,
        stdin_complete=True,
        stdout_raw=b"{}\n",
        stdout_total_byte_count=3,
        stdout_sha256=hashlib.sha256(b"{}\n").hexdigest(),
        stdout_overflow=False,
        stdout_eof=True,
        stderr_prefix=b"",
        stderr_total_byte_count=0,
        stderr_sha256=empty,
        stderr_overflow=False,
        stderr_eof=True,
    )
    fact = launcher._child_fact(observation, stdin_raw=b"abc")  # noqa: SLF001
    assert fact["stdin_sha256"] == hashlib.sha256(b"abc").hexdigest()
    assert fact["stdout_prefix_hex"] == b"{}\n".hex()
    assert fact["stderr_prefix_hex"] == ""
    assert launcher._closed_exactly(observation) is True  # noqa: SLF001


def test_child_timeout_kills_process_group_and_has_a_hard_drain_bound() -> None:
    descriptor = os.open("/bin/sh", os.O_RDONLY | os.O_CLOEXEC)
    started = time.monotonic()
    try:
        observation = launcher._spawn_and_pump(  # noqa: SLF001
            executable_proc_path=(
                f"/proc/{os.getpid()}/fd/{descriptor}"
            ),
            pass_fds=(descriptor,),
            argv=(
                launcher.LOCAL_SSH_EXECUTABLE,
                "-c",
                "sleep 60 & exit 0",
            ),
            stdin_raw=b"x",
            timeout_seconds=0.2,
        )
    finally:
        os.close(descriptor)
    assert time.monotonic() - started < 8.0
    assert observation.timed_out is True
    assert observation.transport_observation_completed_without_local_error is True
    assert launcher._closed_exactly(observation) is False  # noqa: SLF001


def test_observation_is_durable_before_exact_close_is_consumed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[str] = []
    stored: dict[str, bytes] = {}

    class Journal:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def publish_or_verify(self, name: str, raw: bytes) -> None:
            stored.setdefault(name, raw)

        def publish_once(self, name: str, raw: bytes) -> None:
            events.append("publish:" + name)
            assert name not in stored
            stored[name] = raw

        def read(self, name: str, _cap: int = 0) -> bytes:
            return stored[name]

    class Pin:
        descriptor = 90
        proc_path = "/proc/self/fd/90"

        @classmethod
        def open(cls, *_args, **_kwargs):
            events.append("pin")
            return cls()

        def verify(self):
            return None

        def close(self):
            return None

    class Authority:
        @staticmethod
        def build_recovery_inspection_attempt_v42r3r4(**_kwargs):
            ingress = launcher._remote_ingress(  # noqa: SLF001
                recovery_plan={"recovery_plan_id": "f" * 64},
                occurrence={
                    "retained_launch_occurrence_id": "e" * 64,
                    "formal_transport_plan": {
                        "formal_transport_plan_id": launcher.RETAINED_PLAN_ID
                    },
                },
            )
            raw = json.dumps(
                ingress, sort_keys=True, separators=(",", ":")
            ).encode()
            receiver = b"pass\n"
            return {
                "recovery_inspection_attempt_id": "a" * 64,
                "authorized_remote_mode": launcher.REMOTE_MODE,
                "recovery_receiver_artifact": {
                    "byte_count": len(receiver),
                    "sha256": hashlib.sha256(receiver).hexdigest(),
                },
                "canonical_remote_ingress": ingress,
                "canonical_remote_ingress_fact": {
                    "byte_count": len(raw),
                    "sha256": hashlib.sha256(raw).hexdigest(),
                },
                "remote_command_projection": (
                    launcher._actual_remote_command_projection(  # noqa: SLF001
                        receiver, raw, recovery_plan_id="f" * 64
                    )
                ),
            }

        @staticmethod
        def verify_recovery_inspection_attempt_v42r3r4(value, **_kwargs):
            return value if isinstance(value, dict) else json.loads(value)

        @staticmethod
        def build_recovery_transport_ingress_v42r3r4(*, recovery_plan):
            return launcher._remote_ingress(  # noqa: SLF001
                recovery_plan=recovery_plan,
                occurrence={
                    "retained_launch_occurrence_id": "e" * 64,
                    "formal_transport_plan": {
                        "formal_transport_plan_id": launcher.RETAINED_PLAN_ID
                    },
                },
            )

        @staticmethod
        def build_bounded_child_transport_observation_v42r3r4(**_kwargs):
            events.append("build-observation")
            return {
                "bounded_child_transport_observation_id": "b" * 64,
                "process_closed_exactly": False,
            }

        @staticmethod
        def verify_bounded_child_transport_observation_v42r3r4(value, **_kwargs):
            events.append("verify-durable-observation")
            return json.loads(value)

        @staticmethod
        def classify_recovery_v42r3r4(**kwargs):
            observation_name = launcher._inspection_file(  # noqa: SLF001
                launcher.OBSERVATION_PREFIX
            )
            assert observation_name in stored
            assert kwargs["remote_inspection_join"] is None
            events.append("classify")
            return {
                "classification": "AMBIGUOUS_PERMANENTLY_CLOSED",
                "recovery_classification_id": "c" * 64,
            }

        @staticmethod
        def verify_recovery_classification_v42r3r4(value, **_kwargs):
            return json.loads(value)

    empty = hashlib.sha256(b"").hexdigest()
    observation = launcher._ChildObservation(  # noqa: SLF001
        False, None, False, 2, 0, False, b"", 0, empty, False, False,
        b"", 0, empty, False, False,
    )
    monkeypatch.setattr(
        launcher._RecoveryJournal, "open_or_create", classmethod(lambda cls: Journal())
    )
    monkeypatch.setattr(launcher, "_PinnedFile", Pin)
    monkeypatch.setattr(
        launcher, "_spawn_and_pump",
        lambda **_kwargs: (events.append("spawn") or observation),
    )
    monkeypatch.setattr(launcher, "_verify_retained_unchanged", lambda _s: None)
    result, code = launcher._execute_read_only_recovery(  # noqa: SLF001
        authority=Authority(),
        current_raws={launcher.RECEIVER_RELATIVE: b"pass\n"},
        manifest={
            "recovery_controller_source_manifest_id": "d" * 64,
            "recovery_receiver_artifact": {
                "byte_count": len(b"pass\n"),
                "sha256": hashlib.sha256(b"pass\n").hexdigest(),
            },
        },
        occurrence={
            "retained_launch_occurrence_id": "e" * 64,
            "formal_transport_plan": {"formal_transport_plan_id": launcher.RETAINED_PLAN_ID},
        },
        plan={"recovery_plan_id": "f" * 64},
        retained_snapshot=(),
    )
    assert code == 2
    assert result["classification"] == "AMBIGUOUS_PERMANENTLY_CLOSED"
    observation_publish = events.index(
        "publish:" + launcher._inspection_file(launcher.OBSERVATION_PREFIX)  # noqa: SLF001
    )
    attempt_publish = events.index(
        "publish:" + launcher._inspection_file(launcher.ATTEMPT_PREFIX)  # noqa: SLF001
    )
    assert max(index for index, event in enumerate(events) if event == "pin") < (
        attempt_publish
    )
    assert attempt_publish < events.index("spawn")
    assert observation_publish < events.index("verify-durable-observation")
    assert events.index("verify-durable-observation") < events.index("classify")
