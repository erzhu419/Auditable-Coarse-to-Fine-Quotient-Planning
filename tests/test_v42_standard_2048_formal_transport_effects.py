from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import py_compile
import stat
import subprocess
from types import SimpleNamespace

import pytest

from acfqp import construction_k7_standard_2048_formal_transport_v42r1 as formal
from acfqp import (
    construction_k7_standard_2048_materialization_activation_v42r1 as activation,
)
from acfqp import (
    construction_k7_standard_2048_remote_execution_authority_v42r1 as authority,
)
from acfqp.phase3e_ids import canonical_json_bytes
from scripts import run_v42_preformal_upload_sender as frozen_sender
from scripts import run_v42_standard_2048_formal_transport_driver as driver
from scripts import v42_standard_2048_formal_transport_receiver as receiver


RECEIVER_MODULES = {
    "acfqp": "src/acfqp/__init__.py",
    "acfqp.artifacts": "src/acfqp/artifacts.py",
    "acfqp.build_coverage": "src/acfqp/build_coverage.py",
    "acfqp.construction_k7_domain_registry_extension_v42": (
        "src/acfqp/construction_k7_domain_registry_extension_v42.py"
    ),
    "acfqp.construction_k7_standard_2048_formal_transport_v42r1": (
        "src/acfqp/construction_k7_standard_2048_formal_transport_v42r1.py"
    ),
    "acfqp.construction_k7_standard_2048_fresh_terminal_preregistration_v42": (
        "src/acfqp/construction_k7_standard_2048_fresh_terminal_preregistration_v42.py"
    ),
    "acfqp.construction_k7_standard_2048_history_manifest_v42": (
        "src/acfqp/construction_k7_standard_2048_history_manifest_v42.py"
    ),
    "acfqp.construction_k7_standard_2048_materialization_transport_v42r1": (
        "src/acfqp/construction_k7_standard_2048_materialization_transport_v42r1.py"
    ),
    "acfqp.construction_k7_standard_2048_process_supervision_v42r1": (
        "src/acfqp/construction_k7_standard_2048_process_supervision_v42r1.py"
    ),
    "acfqp.construction_k7_standard_2048_remote_execution_authority_v42r1": (
        "src/acfqp/construction_k7_standard_2048_remote_execution_authority_v42r1.py"
    ),
    "acfqp.core": "src/acfqp/core.py",
    "acfqp.enumeration": "src/acfqp/enumeration.py",
    "acfqp.phase3e_ids": "src/acfqp/phase3e_ids.py",
    "scripts": "scripts/__init__.py",
    "scripts.publish_v42_preformal_upload_journal": (
        "scripts/publish_v42_preformal_upload_journal.py"
    ),
    "scripts.run_v42_preformal_upload_sender": (
        "scripts/run_v42_preformal_upload_sender.py"
    ),
    "scripts.run_v42_standard_2048_remote_ordinal2": (
        "scripts/run_v42_standard_2048_remote_ordinal2.py"
    ),
}

RUNNER_MODULES = {
    name: relative
    for name, relative in RECEIVER_MODULES.items()
    if name
    not in {
        "acfqp.construction_k7_standard_2048_formal_transport_v42r1",
        "acfqp.construction_k7_standard_2048_materialization_transport_v42r1",
        "scripts",
        "scripts.publish_v42_preformal_upload_journal",
        "scripts.run_v42_preformal_upload_sender",
        "scripts.run_v42_standard_2048_remote_ordinal2",
    }
}


def _fact(relative: str, raw: bytes) -> dict[str, object]:
    return {
        "relative_path": relative,
        "byte_count": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "git_blob_oid": hashlib.sha1(
            b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw
        ).hexdigest(),
    }


def _write_source(path: Path, raw: bytes) -> dict[str, object]:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    path.chmod(0o444)
    return _fact(str(path), raw)


def _write_control(path: Path, document: dict[str, object]) -> None:
    path.write_bytes(canonical_json_bytes(document))
    path.chmod(0o400)


def _manifested_fixture(
    temporary: Path,
    *,
    entry_relative: str,
    entry_raw: bytes,
    modules: dict[str, str],
    runner_source_only: bool,
) -> tuple[Path, dict[str, object], dict[str, object]]:
    fixed = temporary / "fixed"
    source_root = fixed / "source"
    source_root.mkdir(parents=True)
    facts: list[dict[str, object]] = []
    for relative in modules.values():
        raw = ("VALUE = " + repr(relative) + "\n").encode("utf-8")
        path = source_root / relative
        _write_source(path, raw)
        facts.append(_fact(relative, raw))
    entry_path = source_root / entry_relative
    _write_source(entry_path, entry_raw)
    entry_fact = _fact(entry_relative, entry_raw)
    if runner_source_only:
        facts.append(entry_fact)
    source_payload: dict[str, object] = {
        "schema": "test.execution.source.manifest.v42r1",
        "source_commit": "1" * 40,
        "source_tree": "2" * 40,
        "source_facts": sorted(facts, key=lambda row: str(row["relative_path"])),
    }
    source = {
        **source_payload,
        "source_manifest_id": hashlib.sha256(
            b"acfqp:v42-remote-ordinal2:source-manifest\0"
            + canonical_json_bytes(source_payload)
        ).hexdigest(),
    }
    transport_facts = list(source["source_facts"])
    if not runner_source_only:
        transport_facts.append(entry_fact)
    transport_payload: dict[str, object] = {
        "schema": "test.transport.manifest.v42r1",
        "source_commit": source["source_commit"],
        "source_tree": source["source_tree"],
        "execution_source_manifest_id": source["source_manifest_id"],
        "transport_facts": sorted(
            transport_facts, key=lambda row: str(row["relative_path"])
        ),
    }
    transport = {
        **transport_payload,
        "transport_manifest_id": hashlib.sha256(
            b"acfqp:v42-remote-ordinal2:transport-manifest\0"
            + canonical_json_bytes(transport_payload)
        ).hexdigest(),
    }
    _write_control(fixed / "EXECUTION_SOURCE_MANIFEST.json", source)
    _write_control(fixed / "TRANSPORT_MANIFEST.json", transport)
    return entry_path, source, transport


def _import_lines(modules: dict[str, str]) -> str:
    return "\n".join(
        f"importlib.import_module({name!r})" for name in modules
    )


def test_verified_receiver_loader_real_subprocess_preserves_manifest_ids_and_argv(
    tmp_path: Path,
) -> None:
    marker = tmp_path / "receiver-result.json"
    entry_raw = (
        "import importlib, json, sys\n"
        + _import_lines(RECEIVER_MODULES)
        + "\ndef main(argv=None):\n"
        + f"    open({str(marker)!r}, 'w', encoding='utf-8').write(json.dumps(sys.argv))\n"
        + "    return 0\n"
    ).encode("utf-8")
    entry, source, transport = _manifested_fixture(
        tmp_path,
        entry_relative="scripts/v42_standard_2048_formal_transport_receiver.py",
        entry_raw=entry_raw,
        modules=RECEIVER_MODULES,
        runner_source_only=False,
    )
    command = [
        "/usr/bin/python3", "-I", "-S", "-B", "-c",
        formal.VERIFIED_RECEIVER_LOADER_SOURCE,
        str(entry), hashlib.sha256(entry_raw).hexdigest(), str(len(entry_raw)),
        str(source["source_manifest_id"]), str(transport["transport_manifest_id"]),
        "--prepare-once", "--formal-transport-plan-id", "f" * 64,
    ]
    completed = subprocess.run(
        command, check=False, stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, env={}, timeout=10,
    )
    assert completed.returncode == 0, completed.stderr.decode("utf-8", errors="replace")
    assert json.loads(marker.read_text(encoding="utf-8")) == [
        str(entry), "--prepare-once", "--formal-transport-plan-id", "f" * 64
    ]


def _install_legacy_evil_pyc(source_root: Path, marker: Path) -> None:
    evil_source = source_root / "src/acfqp/evil.py"
    evil_source.parent.mkdir(parents=True, exist_ok=True)
    evil_source.write_text(
        f"open({str(marker)!r}, 'w', encoding='utf-8').write('executed')\n",
        encoding="utf-8",
    )
    py_compile.compile(
        str(evil_source), cfile=str(evil_source.with_suffix(".pyc")), doraise=True
    )
    evil_source.unlink()


def test_verified_receiver_loader_rejects_unmanifested_legacy_pyc(
    tmp_path: Path,
) -> None:
    effect = tmp_path / "evil-receiver-effect"
    entry_raw = (
        "import importlib\n"
        + _import_lines(RECEIVER_MODULES)
        + "\nimportlib.import_module('acfqp.evil')\n"
        + "def main(argv=None): return 0\n"
    ).encode("utf-8")
    entry, source, transport = _manifested_fixture(
        tmp_path,
        entry_relative="scripts/v42_standard_2048_formal_transport_receiver.py",
        entry_raw=entry_raw,
        modules=RECEIVER_MODULES,
        runner_source_only=False,
    )
    _install_legacy_evil_pyc(entry.parents[1], effect)
    completed = subprocess.run(
        [
            "/usr/bin/python3", "-I", "-S", "-B", "-c",
            formal.VERIFIED_RECEIVER_LOADER_SOURCE,
            str(entry), hashlib.sha256(entry_raw).hexdigest(), str(len(entry_raw)),
            str(source["source_manifest_id"]),
            str(transport["transport_manifest_id"]),
            "--prepare-once", "--formal-transport-plan-id", "f" * 64,
        ],
        check=False, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, env={}, timeout=10,
    )
    assert completed.returncode != 0
    assert not effect.exists()


def test_verified_receiver_loader_compiles_actual_receiver_and_exact_closure(
    tmp_path: Path,
) -> None:
    repository = Path(__file__).resolve(strict=True).parents[1]
    fixed = tmp_path / "fixed"
    source_root = fixed / "source"
    source_root.mkdir(parents=True)
    transport_only = {
        "scripts/v42_standard_2048_formal_transport_receiver.py",
        "src/acfqp/construction_k7_standard_2048_formal_transport_v42r1.py",
        "src/acfqp/construction_k7_standard_2048_materialization_transport_v42r1.py",
    }
    source_facts: list[dict[str, object]] = []
    transport_facts: list[dict[str, object]] = []
    for relative in sorted(set(RECEIVER_MODULES.values()) | transport_only):
        raw = (repository / relative).read_bytes()
        destination = source_root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(raw)
        destination.chmod(0o444)
        fact = _fact(relative, raw)
        transport_facts.append(fact)
        if relative not in transport_only:
            source_facts.append(fact)
    source_payload: dict[str, object] = {
        "schema": "test.execution.source.manifest.v42r1",
        "source_commit": "1" * 40,
        "source_tree": "2" * 40,
        "source_facts": source_facts,
    }
    source = {
        **source_payload,
        "source_manifest_id": hashlib.sha256(
            b"acfqp:v42-remote-ordinal2:source-manifest\0"
            + canonical_json_bytes(source_payload)
        ).hexdigest(),
    }
    transport_payload: dict[str, object] = {
        "schema": "test.transport.manifest.v42r1",
        "source_commit": source["source_commit"],
        "source_tree": source["source_tree"],
        "execution_source_manifest_id": source["source_manifest_id"],
        "transport_facts": transport_facts,
    }
    transport = {
        **transport_payload,
        "transport_manifest_id": hashlib.sha256(
            b"acfqp:v42-remote-ordinal2:transport-manifest\0"
            + canonical_json_bytes(transport_payload)
        ).hexdigest(),
    }
    _write_control(fixed / "EXECUTION_SOURCE_MANIFEST.json", source)
    _write_control(fixed / "TRANSPORT_MANIFEST.json", transport)
    entry = source_root / "scripts/v42_standard_2048_formal_transport_receiver.py"
    entry_raw = entry.read_bytes()
    completed = subprocess.run(
        [
            "/usr/bin/python3", "-I", "-S", "-B", "-c",
            formal.VERIFIED_RECEIVER_LOADER_SOURCE,
            str(entry), hashlib.sha256(entry_raw).hexdigest(), str(len(entry_raw)),
            str(source["source_manifest_id"]),
            str(transport["transport_manifest_id"]),
            "--inspect-launch", "--formal-transport-plan-id", "f" * 64,
        ],
        check=False, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, env={}, timeout=10,
    )
    error = completed.stderr.decode("utf-8", errors="replace")
    # The actual receiver reaches its expected empty ingress only after
    # its exact 17-module dependency inventory has been source-only loaded.
    assert completed.returncode != 0
    assert "formal transport ingress is empty" in error
    assert "loaded repository module inventory changed" not in error
    assert "unmanifested repository module" not in error
    assert "escaped verified source bytes" not in error


SERVICE_ENVIRONMENT = {
    "HOME": "/home/erzhu419",
    "LANG": "C.UTF-8",
    "LC_ALL": "C.UTF-8",
    "LOGNAME": "erzhu419",
    "PATH": "/usr/bin:/bin",
    "PYTHONDONTWRITEBYTECODE": "1",
    "PYTHONCOERCECLOCALE": "0",
    "USER": "erzhu419",
}


def _runner_fixture(tmp_path: Path, *, evil: bool) -> tuple[Path, dict[str, object], Path]:
    marker = tmp_path / "runner-result.json"
    evil_line = "importlib.import_module('acfqp.evil')\n" if evil else ""
    entry_raw = (
        "import importlib, json, os, sys\n"
        + _import_lines(RUNNER_MODULES)
        + "\n" + evil_line
        + "def main(argv=None):\n"
        + "    live=[]\n"
        + "    for name in os.listdir('/proc/self/fd'):\n"
        + "        if name.isdigit():\n"
        + "            try: os.fstat(int(name))\n"
        + "            except OSError: continue\n"
        + "            live.append(int(name))\n"
        + f"    open({str(marker)!r}, 'w', encoding='utf-8').write(json.dumps([sys.argv, sorted(live)]))\n"
        + "    return 0\n"
    ).encode("utf-8")
    entry, source, _transport = _manifested_fixture(
        tmp_path,
        entry_relative="scripts/run_v42_standard_2048_remote_ordinal2.py",
        entry_raw=entry_raw,
        modules=RUNNER_MODULES,
        runner_source_only=True,
    )
    if evil:
        _install_legacy_evil_pyc(entry.parents[1], tmp_path / "evil-runner-effect")
    return entry, source, marker


def _runner_pin(path: Path) -> frozen_sender._PinnedLocalFile:  # noqa: SLF001
    descriptor = os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW)
    observed = os.fstat(descriptor)
    raw = path.read_bytes()
    return frozen_sender._PinnedLocalFile(  # noqa: SLF001
        path=str(path), descriptor=descriptor,
        state=frozen_sender._stable_file_state(observed),  # noqa: SLF001
        mode=0o444, uid=os.geteuid(), gid=os.getegid(), nlink=1,
        byte_count=len(raw), sha256=hashlib.sha256(raw).hexdigest(),
        label="test formal runner",
    )


@pytest.mark.parametrize("evil", [False, True])
def test_runner_fd_loader_resets_eof_closes_fd_and_rejects_legacy_pyc(
    tmp_path: Path, evil: bool,
) -> None:
    entry, source, marker = _runner_fixture(tmp_path, evil=evil)
    pin = _runner_pin(entry)
    try:
        pin.verify()
        assert os.lseek(pin.descriptor, 0, os.SEEK_CUR) == pin.byte_count
        completed = subprocess.run(
            [
                "/usr/bin/python3", "-I", "-S", "-B", "-c",
                receiver.VERIFIED_RUNNER_FD_LOADER_SOURCE,
                str(pin.descriptor), str(pin.sha256), str(pin.byte_count),
                str(entry), "--launch-remote", str(source["source_manifest_id"]),
            ],
            check=False, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL, env=SERVICE_ENVIRONMENT,
            pass_fds=(pin.descriptor,), timeout=10,
        )
    finally:
        pin.close()
    if evil:
        assert completed.returncode != 0
        assert not (tmp_path / "evil-runner-effect").exists()
        assert not marker.exists()
    else:
        assert completed.returncode == 0
        assert json.loads(marker.read_text(encoding="utf-8")) == [
            [str(entry), "--launch-remote"], [0, 1, 2]
        ]


def test_existing_runner_exec_uses_exact_service_environment_and_pinned_fds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[tuple[object, ...]] = []

    class Pin:
        def __init__(self, descriptor: int) -> None:
            self.descriptor = descriptor
            self.sha256 = "a" * 64
            self.byte_count = 123

        def verify(self) -> None:
            events.append(("verify", self.descriptor))

        def close(self) -> None:
            events.append(("close", self.descriptor))

    python_pin = Pin(91)
    runner_pin = Pin(92)
    monkeypatch.setattr(receiver, "_verify_program_self", lambda _plan: None)
    monkeypatch.setattr(
        authority, "verify_live_source_matches_manifest_v42",
        lambda _root, _manifest: None,
    )
    monkeypatch.setattr(receiver, "_open_tool_pin", lambda *_args: python_pin)
    monkeypatch.setattr(
        receiver, "_open_manifested_runner_pin", lambda **_kwargs: runner_pin
    )

    def fake_fcntl(fd: int, command: int, value: int | None = None) -> int:
        events.append(("fcntl", fd, command, value))
        return receiver.fcntl.FD_CLOEXEC

    class ExecIntercept(BaseException):
        pass

    def fake_execve(path: str, argv: tuple[str, ...], environment: dict[str, str]) -> None:
        events.append(("execve", path, argv, environment))
        raise ExecIntercept

    monkeypatch.setattr(receiver.fcntl, "fcntl", fake_fcntl)
    monkeypatch.setattr(receiver.os, "execve", fake_execve)
    plan = {
        "source_manifest_id": "b" * 64,
    }
    with pytest.raises(ExecIntercept):
        receiver._exec_existing_runner(  # noqa: SLF001
            plan=plan, source_manifest={}, mode="--launch-remote"
        )
    exec_event = next(event for event in events if event[0] == "execve")
    assert exec_event[1] == "/proc/self/fd/91"
    assert exec_event[2][0:6] == (
        authority.REMOTE_PYTHON, "-I", "-S", "-B", "-c",
        receiver.VERIFIED_RUNNER_FD_LOADER_SOURCE,
    )
    assert exec_event[2][6:] == (
        "92", "a" * 64, "123",
        str(authority.REMOTE_SOURCE_ROOT / formal.FORMAL_RUNNER_RELATIVE),
        "--launch-remote", "b" * 64,
    )
    assert exec_event[3] == formal.FORMAL_SERVICE_ENVIRONMENT
    assert ("close", 91) in events and ("close", 92) in events


def test_local_verified_finder_handles_stdlib_and_rejects_repeat_loader(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    class RootPin:
        def verify(self) -> None:
            pass

    root = tmp_path / "repo"
    source = root / "src"
    source.mkdir(parents=True)
    monkeypatch.setattr(driver, "ROOT", root)
    monkeypatch.setattr(driver, "SOURCE_ROOT", source)
    raw = b"# verified package\n"
    fact = _fact("src/acfqp/__init__.py", raw)
    finder = driver._VerifiedSourceFinder(  # noqa: SLF001
        {"src/acfqp/__init__.py": fact},
        read_source=lambda _relative: raw,
        pinned_root_chain=RootPin(),
    )
    assert finder.find_spec("json", None) is None
    shadow = root / "json.pyc"
    shadow.write_bytes(b"shadow")
    with pytest.raises(ImportError, match="stdlib shadow"):
        finder.find_spec("json", None)
    first = finder.find_spec("acfqp", None)
    assert first is not None
    with pytest.raises(ImportError, match="loader repeated"):
        finder.find_spec("acfqp", None)


def test_artifact_states_rejects_stale_prepare_failure_chain(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    from tests import test_construction_k7_standard_2048_formal_transport_v42r1 as fixture
    from scripts import run_v42_standard_2048_remote_ordinal2 as existing_runner

    plan = fixture._plan()  # noqa: SLF001
    source_root = tmp_path / "source"
    source_root.mkdir()
    remote_control = tmp_path / "control"
    remote_control.mkdir()
    formal_journal = tmp_path / "formal"
    formal_journal.mkdir()
    monkeypatch.setattr(receiver, "ROOT", source_root)
    monkeypatch.setattr(authority, "REMOTE_ROOT", remote_control)
    monkeypatch.setattr(authority, "REMOTE_SOURCE_ROOT", source_root)
    monkeypatch.setattr(formal, "REMOTE_FORMAL_JOURNAL_ROOT", formal_journal)
    attempt = existing_runner._journal(  # noqa: SLF001
        schema="acfqp.v42_remote_ordinal2_prepare_attempt_journal.v42r1",
        domain="acfqp:v42-remote-ordinal2:prepare-journal",
        id_key="prepare_attempt_journal_id",
        fields={
            "formal_identity": authority.FORMAL_IDENTITY,
            "global_execution_ordinal": authority.GLOBAL_EXECUTION_ORDINAL,
            "source_commit": plan["source_commit"],
            "source_tree": plan["source_tree"],
            # A self-consistent old attempt is not the current plan's chain.
            "source_manifest_id": "0" * 64,
            "transport_manifest_id": plan["transport_manifest_id"],
            "remote_host_alias": authority.REMOTE_HOST_ALIAS,
            "remote_hostname": authority.REMOTE_HOSTNAME,
            "prepare_ordinal": authority.GLOBAL_EXECUTION_ORDINAL,
            "outcome_or_tape_materialized": False,
            "formal_execution_performed": False,
            "same_identity_prepare_retry_forbidden": True,
        },
    )
    failure = existing_runner._journal(  # noqa: SLF001
        schema="acfqp.v42_remote_ordinal2_prepare_failure_journal.v42r1",
        domain="acfqp:v42-remote-ordinal2:prepare-journal",
        id_key="prepare_failure_journal_id",
        fields={
            "formal_identity": authority.FORMAL_IDENTITY,
            "global_execution_ordinal": authority.GLOBAL_EXECUTION_ORDINAL,
            "prepare_attempt_journal_id": attempt["prepare_attempt_journal_id"],
            "failure_stage": "PREDECESSOR_AND_TRANSPORT_PREFLIGHT",
            "failure_type": "RuntimeError",
            "failure_message": "retained stale failure",
            "authority_root_state": "ABSENT",
            "evidence_root_state": "ABSENT",
            "prepare_receipt_state": "ABSENT",
            "outcome_or_tape_materialized": False,
            "formal_execution_performed": False,
            "same_identity_prepare_retry_forbidden": True,
        },
    )
    _write_control(
        source_root / authority.PREPARE_ATTEMPT_JOURNAL_NAME, attempt
    )
    _write_control(
        source_root / authority.PREPARE_FAILURE_JOURNAL_NAME, failure
    )
    states = receiver._artifact_states(  # noqa: SLF001
        plan=plan, operation=formal.OPERATION_PREPARE,
        attempt_id="0" * 64, prepare_receipt=None,
    )
    assert states["prepare_receipt"] == "ABSENT"
    assert states["prepare_failure"] == "PRESENT_INVALID"


def test_artifact_states_projects_real_verified_fail_closed_terminal(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    from acfqp import construction_k7_standard_2048_fresh_terminal_preregistration_v42 as pre
    from scripts import run_v42_standard_2048_remote_ordinal2 as existing_runner
    from scripts import supervise_v42_standard_2048_remote_ordinal2 as supervisor
    from tests import test_construction_k7_standard_2048_formal_transport_v42r1 as fixture
    from tests import test_run_v42_standard_2048_remote_ordinal2 as runner_fixture

    documents = runner_fixture._authority_documents()  # noqa: SLF001
    receipt = documents["receipt"]
    local_attempt = documents["local_attempt"]
    runner_attempt = documents["attempt"]
    worker_start = authority.build_worker_start_v42(
        prepare_receipt=receipt,
        runner_attempt=runner_attempt,
        worker_authorization_secret_sha256="d" * 64,
    )
    consumption = authority.build_authority_consumption_v42(
        prepare_receipt=receipt,
        runner_attempt=runner_attempt,
        worker_start=worker_start,
    )
    campaign_payload = {"all_registered_episodes_terminal": False}
    campaign = {
        **campaign_payload,
        "fresh_terminal_campaign_id": existing_runner.domains.extension_content_id_v42(
            existing_runner.domains.CONSTRUCTION_K7_CAMPAIGN_V42_DOMAIN,
            campaign_payload,
        ),
    }
    verification_payload = {
        "fresh_terminal_campaign_id": campaign["fresh_terminal_campaign_id"],
        "prepare_receipt_id": receipt["prepare_receipt_id"],
        "runner_attempt_id": runner_attempt["runner_attempt_id"],
        "worker_start_id": worker_start["worker_start_id"],
        "authority_consumption_id": consumption["authority_consumption_id"],
        "producer_or_runner_module_imported": False,
    }
    verification = {
        **verification_payload,
        "fresh_terminal_verification_id": existing_runner.domains.extension_content_id_v42(
            existing_runner.domains.CONSTRUCTION_K7_VERIFICATION_V42_DOMAIN,
            verification_payload,
        ),
    }
    envelope = supervisor._build_supervisor_envelope(  # noqa: SLF001
        receipt=receipt,
        attempt=runner_attempt,
        worker_start=worker_start,
        consumption=consumption,
        campaign_document=campaign,
        verification_document=verification,
        all_terminal=False,
    )
    raw_by_role: dict[str, bytes] = {
        "LOCAL_MATERIALIZATION_ATTEMPT": canonical_json_bytes(
            documents["materialization_local"]
        ),
        "SOURCE_CAPSULE": documents["capsule"]["raw"],
        "SOURCE_MANIFEST": canonical_json_bytes(documents["source"]),
        "TRANSPORT_MANIFEST": canonical_json_bytes(documents["transport"]),
        "REMOTE_BOOTSTRAP_PYZ": documents["pyz"]["raw"],
        "REMOTE_MATERIALIZATION_ATTEMPT": canonical_json_bytes(
            documents["materialization_remote"]
        ),
        "MATERIALIZATION_TERMINAL": canonical_json_bytes(
            documents["materialization_terminal"]
        ),
        "LOCAL_LAUNCH_ATTEMPT": canonical_json_bytes(local_attempt),
        "PREPARE_HOST_ATTESTATION": canonical_json_bytes(documents["prepare_host"]),
        "LAUNCH_HOST_ATTESTATION": canonical_json_bytes(documents["launch_host"]),
        "PREPARE_ATTEMPT": canonical_json_bytes(documents["prepare_journal"]),
        "PREPARE_RECEIPT": canonical_json_bytes(receipt),
        "LAUNCH_ATTEMPT": canonical_json_bytes(documents["launch_journal"]),
        "ATTEMPT": canonical_json_bytes(runner_attempt),
        "WORKER_START": canonical_json_bytes(worker_start),
        "AUTHORITY_CONSUMPTION": canonical_json_bytes(consumption),
        "SUPERVISOR_STDOUT": canonical_json_bytes(envelope) + b"\n",
        "SUPERVISOR_STDERR": b"",
        "CAMPAIGN": canonical_json_bytes(campaign),
        "VERIFICATION": canonical_json_bytes(verification),
    }
    terminal_payload = {
        "schema": "acfqp.v42_remote_ordinal2_runner_terminal.v42r1",
        "schema_version": authority.SCHEMA_VERSION,
        "formal_identity": authority.FORMAL_IDENTITY,
        "global_execution_ordinal": authority.GLOBAL_EXECUTION_ORDINAL,
        "prepare_receipt_id": receipt["prepare_receipt_id"],
        "runner_attempt_id": runner_attempt["runner_attempt_id"],
        "launch_attempt_journal_id": documents["launch_journal"][
            "launch_attempt_journal_id"
        ],
        "source_manifest_id": receipt["source_manifest_id"],
        "transport_manifest_id": receipt["transport_manifest_id"],
        "predecessor_binding_id": receipt["predecessor_binding_id"],
        "local_launch_attempt_id": local_attempt["local_launch_attempt_id"],
        "attempt_artifact": existing_runner._write_fact(  # noqa: SLF001
            raw_by_role["ATTEMPT"], authority.ATTEMPT_NAME
        ),
        "worker_start_artifact": {
            **existing_runner._stream_fact(  # noqa: SLF001
                raw_by_role["WORKER_START"], 1024 * 1024
            ),
            "relative_name": authority.WORKER_START_NAME,
        },
        "authority_consumption_artifact": {
            **existing_runner._stream_fact(  # noqa: SLF001
                raw_by_role["AUTHORITY_CONSUMPTION"], 1024 * 1024
            ),
            "relative_name": authority.AUTHORITY_CONSUMPTION_NAME,
        },
        "campaign_artifact": existing_runner._write_fact(  # noqa: SLF001
            raw_by_role["CAMPAIGN"], authority.CAMPAIGN_NAME
        ),
        "verification_artifact": existing_runner._write_fact(  # noqa: SLF001
            raw_by_role["VERIFICATION"], authority.VERIFICATION_NAME
        ),
        "supervisor_stdout_artifact": existing_runner._write_fact(  # noqa: SLF001
            raw_by_role["SUPERVISOR_STDOUT"], authority.SUPERVISOR_STDOUT_NAME
        ),
        "supervisor_stderr_artifact": existing_runner._write_fact(  # noqa: SLF001
            raw_by_role["SUPERVISOR_STDERR"], authority.SUPERVISOR_STDERR_NAME
        ),
        "status": "FAIL_CLOSED_ACTIVE_AT_2048_DECISION_CAP",
        "scientific_success": False,
        "all_registered_episodes_terminal": False,
        "same_identity_rerun_forbidden": True,
        "official_execution_allowed": False,
    }
    terminal = {
        **terminal_payload,
        "runner_terminal_id": existing_runner._content_id(  # noqa: SLF001
            "acfqp:v42-remote-ordinal2:runner-terminal", terminal_payload
        ),
    }
    raw_by_role["TERMINAL"] = canonical_json_bytes(terminal)
    assert existing_runner._verify_collected_artifacts(  # noqa: SLF001
        raw_by_role,
        local_receipt_raw=raw_by_role["PREPARE_RECEIPT"],
        receipt=receipt,
        local_attempt_raw=raw_by_role["LOCAL_LAUNCH_ATTEMPT"],
        local_attempt=local_attempt,
    ) == "COMPLETE_TERMINAL"

    source_root = tmp_path / "source"
    remote_control = tmp_path / "control"
    source_root.mkdir()
    remote_control.mkdir()
    collection_sources = existing_runner._collection_sources(  # noqa: SLF001
        source_root, remote_control
    )
    for role, path, _cap in collection_sources:
        if role in raw_by_role:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw_by_role[role])
            path.chmod(0o400)
    formal_journal = tmp_path / "formal"
    formal_journal.mkdir()
    monkeypatch.setattr(receiver, "ROOT", source_root)
    monkeypatch.setattr(formal, "REMOTE_FORMAL_JOURNAL_ROOT", formal_journal)
    monkeypatch.setattr(
        existing_runner, "_collection_sources",  # noqa: SLF001
        lambda _source, _control: collection_sources,
    )
    monkeypatch.setattr(
        receiver, "_prepare_receipt",
        lambda _plan: (receipt, raw_by_role["PREPARE_RECEIPT"]),
    )
    original_stable = receiver._stable_regular  # noqa: SLF001
    local_attempt_path = authority.REMOTE_ROOT / authority.LOCAL_LAUNCH_ATTEMPT_NAME
    fixture_local_attempt_path = (
        remote_control / authority.LOCAL_LAUNCH_ATTEMPT_NAME
    )

    def redirected_stable(path: Path, cap: int):  # type: ignore[no-untyped-def]
        return original_stable(
            fixture_local_attempt_path if path == local_attempt_path else path,
            cap,
        )

    monkeypatch.setattr(receiver, "_stable_regular", redirected_stable)
    plan = dict(fixture._plan())  # noqa: SLF001
    for field in (
        "source_commit", "source_tree", "source_manifest_id", "transport_manifest_id"
    ):
        plan[field] = receipt[field]
    states = receiver._artifact_states(  # noqa: SLF001
        plan=plan, operation=formal.OPERATION_LAUNCH,
        attempt_id=local_attempt["local_launch_attempt_id"],
        prepare_receipt=receipt,
    )
    assert states["launch_attempt_journal"] == "EXACT"
    assert states["runner_failure"] == "ABSENT"
    assert states["scientific_terminal"] == "EXACT_FAIL_CLOSED"


def _make_journal(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    parent = tmp_path / "outer" / "inner"
    parent.mkdir(parents=True)
    root = parent / "formal-journal"
    monkeypatch.setattr(formal, "LOCAL_FORMAL_JOURNAL_ROOT", root)
    driver._ensure_journal_root()  # noqa: SLF001
    return root


def test_journal_publish_is_mode_0400_under_hostile_umask_and_root_is_rejoined(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    root = _make_journal(monkeypatch, tmp_path)
    previous = os.umask(0o777)
    try:
        driver._publish_once(root / "ONE.json", b"{}")  # noqa: SLF001
    finally:
        os.umask(previous)
    assert stat.S_IMODE((root / "ONE.json").stat().st_mode) == 0o400
    original = root.with_name(root.name + ".old")
    root.rename(original)
    root.mkdir(mode=0o700)
    with pytest.raises(driver.V42FormalTransportDriverError, match="identity"):
        driver._JournalPin.open()  # noqa: SLF001


def test_outer_cut_survives_inner_marker_unlink_and_parent_component_swap_is_seen(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    root = _make_journal(monkeypatch, tmp_path)
    attempt_id = "a" * 64
    operation = "prepare_once"
    marker = root / formal.LOCAL_PREPARE_NETWORK_START_NAME
    cut_name = driver._journal_anchor_name(  # noqa: SLF001
        "NETWORK_START." + operation + "." + attempt_id + ".json"
    )
    pin = driver._JournalPin.open()  # noqa: SLF001
    try:
        pin.publish_parent_anchor(cut_name, b"cut")
        pin.publish(marker.name, b"inner")
        marker.unlink()
        assert pin.parent_anchor_exists(cut_name)
        ancestor = root.parents[1]
        moved = ancestor.with_name(ancestor.name + ".moved")
        ancestor.rename(moved)
        ancestor.mkdir()
        with pytest.raises(
            driver.V42FormalTransportDriverError, match="directory component"
        ):
            pin.verify_root()
    finally:
        pin.close()


def test_external_cut_is_durable_before_inner_marker_async_failure(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    from types import SimpleNamespace
    from tests import test_construction_k7_standard_2048_formal_transport_v42r1 as fixture

    root = _make_journal(monkeypatch, tmp_path)
    plan = fixture._plan()  # noqa: SLF001
    attempt = formal.build_prepare_attempt_v42r1(plan)
    attempt_id = attempt["formal_prepare_attempt_id"]
    marker = root / formal.LOCAL_PREPARE_NETWORK_START_NAME
    effects = 0

    class Pins:
        ssh = SimpleNamespace(descriptor=99)

        def verify(self) -> None:
            pass

        def close(self) -> None:
            pass

    class Prepared:
        def verify_prepared(self) -> None:
            pass

        def spawn_and_pump(self) -> None:
            nonlocal effects
            effects += 1

        def close(self) -> None:
            pass

    class Sigpipe:
        def verify(self) -> None:
            pass

        def close(self) -> None:
            pass

    monkeypatch.setattr(
        frozen_sender, "_open_local_dispatch_pins_v42r1", lambda _plan: Pins()
    )
    monkeypatch.setattr(
        frozen_sender, "_derive_identity_fingerprint_v42r1",
        lambda **_kwargs: plan["ssh_client_contract"]["identity_public_fingerprint"],
    )
    monkeypatch.setattr(
        driver, "_prepare_formal_pinned_child", lambda **_kwargs: Prepared()
    )
    monkeypatch.setattr(
        frozen_sender._SigpipeIgnoreGuard,  # noqa: SLF001
        "acquire", classmethod(lambda _cls: Sigpipe()),
    )
    original_publish = driver._JournalPin.publish  # noqa: SLF001

    class InjectedAsyncFailure(BaseException):
        pass

    def fail_inner_publish(
        _self: object, _name: str, _raw: bytes,
    ) -> tuple[int, ...]:
        raise InjectedAsyncFailure("after external cut before inner marker")

    monkeypatch.setattr(driver._JournalPin, "publish", fail_inner_publish)  # noqa: SLF001
    observation, marker_may_exist, failure = driver._dispatch_effect_once(  # noqa: SLF001
        plan=plan, operation="prepare_once", attempt_id=attempt_id,
        ingress_raw=b"{}", marker_path=marker,
        stdout_cap=1024, timeout=1.0,
    )
    assert observation is None
    assert marker_may_exist is True
    assert isinstance(failure, InjectedAsyncFailure)
    assert effects == 0
    assert not marker.exists()
    external = root.parent / driver._journal_anchor_name(  # noqa: SLF001
        "NETWORK_START.prepare_once." + attempt_id + ".json"
    )
    assert external.is_file()
    monkeypatch.setattr(driver._JournalPin, "publish", original_publish)  # noqa: SLF001
    with pytest.raises(driver.V42FormalTransportDriverError, match="replay is forbidden"):
        driver._dispatch_effect_once(  # noqa: SLF001
            plan=plan, operation="prepare_once", attempt_id=attempt_id,
            ingress_raw=b"{}", marker_path=marker,
            stdout_cap=1024, timeout=1.0,
        )
    assert effects == 0


def _collector_success_fixture() -> tuple[dict[str, object], dict[str, object]]:
    activation_plan = {"materialization_activation_plan_id": "1" * 64}
    local = {"local_materialization_activation_attempt_id": "2" * 64}
    network: dict[str, object] = {}
    remote = {"remote_materialization_activation_attempt_id": "3" * 64}
    service: dict[str, object] = {}
    ready: dict[str, object] = {}
    terminal = {"remote_materialization_transport_terminal_id": "4" * 64}
    remote_materialization = {"remote_materialization_attempt_id": "5" * 64}
    bootstrap = {"materialization_terminal_id": "6" * 64}
    fixed_documents = {
        authority.SOURCE_MANIFEST_NAME: {"value": "source"},
        authority.TRANSPORT_MANIFEST_NAME: {"value": "transport"},
        authority.LOCAL_MATERIALIZATION_ATTEMPT_NAME: {"value": "local"},
        authority.REMOTE_MATERIALIZATION_ATTEMPT_NAME: remote_materialization,
        authority.MATERIALIZATION_TERMINAL_NAME: bootstrap,
    }
    state = {"stable": True}
    observed = {
        "schema": "acfqp.v42_remote_ordinal2_materialization_activation_read_only_observation.v42r1",
        "materialization_activation_plan_id": "1" * 64,
        "local_materialization_activation_attempt_id": "2" * 64,
        "observation_before": state,
        "observation_after": state,
        "remote_documents": {
            "remote_attempt": remote,
            "service_receipt": service,
            "publish_ready": ready,
            "terminal": terminal,
            "failure": None,
        },
        "fixed_root_evidence": {
            "inventory_before": sorted(fixed_documents),
            "inventory_after": sorted(fixed_documents),
            "documents": fixed_documents,
            "collected_subset_only_not_whole_tree": True,
        },
        "remote_mutation_performed": False,
        "only_read_only_ssh_ingress_and_systemctl_query_processes_started": True,
        "additional_durable_or_mutating_remote_process_started": False,
        "activation_retry_authorized": False,
    }
    classification = {
        "classification": activation.CLASSIFICATION_SUCCESS,
        "reason": "DURABLE_TERMINAL_AND_EXACT_FIXED_FIVE_CONTROLS",
        "materialization_activation_classification_id": "7" * 64,
        "remote_materialization_transport_terminal_id": "4" * 64,
    }
    snapshot_payload = {
        "schema": "acfqp.v42_materialization_activation_read_only_snapshot.v42r1",
        "materialization_activation_plan_id": "1" * 64,
        "snapshot_ordinal": 1,
        "previous_snapshot_id": None,
        "observation": observed,
        "classification": classification,
        "remote_observation_only": True,
        "activation_effect_replay_authorized": False,
    }
    snapshot = {
        **snapshot_payload,
        "activation_read_only_snapshot_id": hashlib.sha256(
            b"acfqp:v42-remote-ordinal2:activation-read-only-snapshot\0"
            + canonical_json_bytes(snapshot_payload)
        ).hexdigest(),
    }
    final_payload = {
        "schema": "acfqp.v42_materialization_activation_final_evidence_index.v42r1",
        "materialization_activation_plan_id": "1" * 64,
        "activation_read_only_snapshot_id": snapshot[
            "activation_read_only_snapshot_id"
        ],
        "activation_classification_id": "7" * 64,
        "remote_materialization_transport_terminal_id": "4" * 64,
        "remote_materialization_attempt_id": "5" * 64,
        "materialization_terminal_id": "6" * 64,
        "activation_service_terminal_before_exact_bootstrap_exec_protocol_verified": True,
        "bootstrap_terminal_exact_shared_materialization_ids_verified": True,
        "bootstrap_launcher_consumed_activation_transport_terminal_id": False,
        "downstream_launcher_terminal_id_join_remains_defense_in_depth": True,
        "formal_evidence_bundle_complete_under_bounded_successor_claim": True,
        "same_uid_coordinated_replacement_of_named_root_and_all_persistent_anchors_excluded_from_claim": True,
    }
    final = {
        **final_payload,
        "materialization_activation_final_evidence_index_id": hashlib.sha256(
            b"acfqp:v42-remote-ordinal2:activation-final-evidence-index\0"
            + canonical_json_bytes(final_payload)
        ).hexdigest(),
    }
    inputs: dict[str, object] = {
        "activation_read_only_snapshots": [snapshot],
        "activation_final_evidence_index": final,
        "documents": fixed_documents,
    }
    arguments: dict[str, object] = {
        "inputs": inputs,
        "activation_plan": activation_plan,
        "local_activation": local,
        "network_start": network,
        "preformal_receipt": {},
        "remote_activation": remote,
        "service": service,
        "ready": ready,
        "activation_terminal": terminal,
        "remote_materialization": remote_materialization,
        "bootstrap_terminal": bootstrap,
    }
    return arguments, classification


def test_formal_requires_final_index_selected_snapshot_to_be_chain_tail(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    arguments, classification = _collector_success_fixture()
    monkeypatch.setattr(
        activation,
        "verify_materialization_activation_classification_v42r1",
        lambda *_args, **_kwargs: classification,
    )
    assert driver._verify_activation_collector_success(  # noqa: SLF001
        **arguments
    ) == classification
    inputs = arguments["inputs"]
    assert isinstance(inputs, dict)
    snapshots = inputs["activation_read_only_snapshots"]
    assert isinstance(snapshots, list)
    first = snapshots[0]
    second_payload = dict(first)
    second_payload.pop("activation_read_only_snapshot_id")
    second_payload["snapshot_ordinal"] = 2
    second_payload["previous_snapshot_id"] = first[
        "activation_read_only_snapshot_id"
    ]
    second = {
        **second_payload,
        "activation_read_only_snapshot_id": hashlib.sha256(
            b"acfqp:v42-remote-ordinal2:activation-read-only-snapshot\0"
            + canonical_json_bytes(second_payload)
        ).hexdigest(),
    }
    inputs["activation_read_only_snapshots"] = [first, second]
    with pytest.raises(
        driver.V42FormalTransportDriverError, match="snapshot tail"
    ):
        driver._verify_activation_collector_success(**arguments)  # noqa: SLF001


def test_activation_collector_split_root_loads_directly_and_expected_id_is_required(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    from acfqp import (
        construction_k7_standard_2048_materialization_transport_v42r1 as preformal,
    )
    from scripts import run_v42_materialization_activation as activation_driver
    from tests import (
        test_construction_k7_standard_2048_materialization_activation_v42r1
        as activation_fixture,
    )
    from tests import (
        test_construction_k7_standard_2048_materialization_transport_v42r1
        as preformal_fixture,
    )

    chain = activation_fixture._chain()  # noqa: SLF001
    bootstrap_documents = activation_fixture._bootstrap_success_documents(  # noqa: SLF001
        chain
    )
    classification = activation_fixture._classify(  # noqa: SLF001
        chain, stage="terminal", service=True, ready=True, terminal=True
    )
    observation = activation_fixture._observation(chain, stage="terminal")  # noqa: SLF001
    fixed_inventory = sorted(
        set(preformal.CONTROL_NAMES) | set(bootstrap_documents)
    )
    observed = {
        "schema": "acfqp.v42_remote_ordinal2_materialization_activation_read_only_observation.v42r1",
        "materialization_activation_plan_id": chain["activation_plan"][
            "materialization_activation_plan_id"
        ],
        "local_materialization_activation_attempt_id": chain["local_attempt"][
            "local_materialization_activation_attempt_id"
        ],
        "observation_before": observation,
        "observation_after": observation,
        "remote_documents": {
            "remote_attempt": chain["remote_attempt"],
            "service_receipt": chain["service_receipt"],
            "publish_ready": chain["ready"],
            "terminal": chain["terminal"],
            "failure": None,
        },
        "fixed_root_evidence": {
            "inventory_before": fixed_inventory,
            "inventory_after": fixed_inventory,
            "documents": bootstrap_documents,
            "collected_subset_only_not_whole_tree": True,
        },
        "remote_mutation_performed": False,
        "only_read_only_ssh_ingress_and_systemctl_query_processes_started": True,
        "additional_durable_or_mutating_remote_process_started": False,
        "activation_retry_authorized": False,
    }
    controls = tmp_path / "controls"
    controls.mkdir(mode=0o700)
    for name, raw in chain["controls"].items():
        path = controls / name
        path.write_bytes(raw)
        path.chmod(0o400)
    evidence = tmp_path / "activation-evidence"
    activation_driver._persist_read_only_classification_evidence(  # noqa: SLF001
        evidence_root=str(evidence),
        activation_plan=chain["activation_plan"],
        local_attempt=chain["local_attempt"],
        network_start=chain["network_start"],
        preformal_receipt=chain["receipt"],
        observed=observed,
        classification=classification,
        preformal_plan=chain["plan"],
        preformal_attempt=chain["attempt"],
        preformal_outcome=chain["outcome"],
        resource_plan=chain["resource_plan"],
        resource_result=chain["resource_result"],
        control_root=str(controls),
    )
    final = json.loads(
        (evidence / driver.ACTIVATION_FINAL_EVIDENCE_INDEX_FILE).read_text(
            encoding="utf-8"
        )
    )
    preformal_context = preformal_fixture._context()  # noqa: SLF001
    program_raw = {
        preformal.PREFORMAL_LOADER_SOURCE_RELATIVE: preformal_context[
            "loader_source_raw"
        ],
        preformal.PREFORMAL_RECEIVER_SOURCE_RELATIVE: preformal_context[
            "receiver_source_raw"
        ],
        driver.ACTIVATION_LOADER_RELATIVE: activation_fixture._LOADER_RAW,  # noqa: SLF001
        driver.ACTIVATION_RECEIVER_RELATIVE: activation_fixture._RECEIVER_RAW,  # noqa: SLF001
        driver.ACTIVATION_SERVICE_RELATIVE: activation_fixture._SERVICE_RAW,  # noqa: SLF001
        driver.ACTIVATION_DRIVER_RELATIVE: activation_fixture._DRIVER_RAW,  # noqa: SLF001
        driver.ACTIVATION_AUTHORITY_RELATIVE: (
            activation_fixture._ACTIVATION_AUTHORITY_RAW  # noqa: SLF001
        ),
    }
    monkeypatch.setattr(driver, "_program_raw", lambda relative: program_raw[relative])
    final_id = final["materialization_activation_final_evidence_index_id"]
    inputs = driver._load_production_inputs(  # noqa: SLF001
        evidence, expected_final_evidence_index_id=final_id
    )
    core, terminal_raw = driver._verify_production_activation_chain(inputs)  # noqa: SLF001
    assert core["materialization_activation_final_evidence_index_id"] == final_id
    assert terminal_raw == (evidence / driver.ACTIVATION_TERMINAL_FILE).read_bytes()
    with pytest.raises(
        driver.V42FormalTransportDriverError, match="differs from expected"
    ):
        driver._load_production_inputs(  # noqa: SLF001
            evidence, expected_final_evidence_index_id="0" * 64
        )
