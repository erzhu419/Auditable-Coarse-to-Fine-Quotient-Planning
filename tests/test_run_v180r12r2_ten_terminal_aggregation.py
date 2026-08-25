from __future__ import annotations

import ast
import hashlib
import importlib.util
import inspect
import json
from pathlib import Path
from types import SimpleNamespace

import pytest


ROOT = Path(__file__).resolve().parents[1]


def _load_runner(filename: str, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, ROOT / "scripts" / filename)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_v180r12r2_production_runner_is_one_shot_and_evidence_first() -> None:
    path = ROOT / "scripts/run_v180r12r2_ten_terminal_aggregation.py"
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    main = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "main"
    )
    first = main.body[0]
    assert isinstance(first, ast.Assign)
    assert "freeze_ten_terminal_aggregation_authorization_evidence_v180r12r2" in ast.unparse(first)
    assert 'os.environ[\'ACFQP_V180R12R2_PREREG_COMMIT\']' in ast.unparse(first)
    assert "os.O_EXCL" in source
    assert "resource.RLIMIT_AS" in source
    assert "signal.alarm(authorization.TIMEOUT_SECONDS)" in source
    assert "freeze_ten_terminal_aggregation_v180r12r2" in source
    assert "verify_ten_terminal_aggregation_independently_v180r12r2" not in source
    authorized_try = next(
        node
        for node in main.body
        if isinstance(node, ast.Try)
        and "resource.getrlimit" in ast.unparse(node)
    )
    authorized_source = ast.unparse(authorized_try)
    assert "os.mkdir(OUTPUT_ROOT" in authorized_source
    assert "os.fsync(parent_fd)" in authorized_source
    assert "resource.setrlimit" in authorized_source
    assert "_release_preexecution_heap_and_require_cap_headroom" in authorized_source
    assert "signal.signal" in authorized_source
    assert "_failure" in authorized_source
    assert "_restore_alarm" in authorized_source
    assert "_suppress_alarm_before_reserve_release" in authorized_source
    assert "_complete_alarm_cleanup_after_reserve_release" in authorized_source
    assert "_alarm_cleanup_observation" in authorized_source
    assert "FAILURE_EMERGENCY_RESERVE_BYTES" in authorized_source
    assert authorized_source.index("_suppress_alarm_before_reserve_release") < (
        authorized_source.index("emergency_failure_reserve.clear")
    ) < authorized_source.index("_complete_alarm_cleanup_after_reserve_release")
    assert "git push" not in source


def test_v180r12r2_production_failure_survives_partial_terminal(
    monkeypatch, tmp_path: Path
) -> None:
    runner = _load_runner(
        "run_v180r12r2_ten_terminal_aggregation.py",
        "_v180r12r2_production_runner_partial_test",
    )
    exact = tmp_path / "exact-freeze"
    output = exact / "output"
    output.mkdir(parents=True)
    terminal = output / "TERMINAL.json"
    terminal.write_bytes(b"partial-terminal")
    failure = exact / "FAILURE.json"
    monkeypatch.setattr(runner, "ROOT", tmp_path)
    monkeypatch.setattr(runner, "OUTPUT_ROOT", output)
    monkeypatch.setattr(runner, "RUNTIME_CAS_ROOT", exact / "cas")
    monkeypatch.setattr(runner, "TERMINAL", terminal)
    monkeypatch.setattr(runner, "FAILURE", failure)

    runner._failure(
        "RuntimeError",
        "injected post-create write failure",
        failure_message_truncated=False,
        alarm_teardown_failure=None,
        authorization_id="a" * 64,
        protocol_id="b" * 64,
        authorization_evidence_id="c" * 64,
    )
    document = json.loads(failure.read_bytes())
    assert document["terminal_output_present"] is True
    assert document["terminal_output_observation"] == {
        "state": "PRESENT",
        "byte_count": len(b"partial-terminal"),
        "sha256": hashlib.sha256(b"partial-terminal").hexdigest(),
    }
    assert document["same_authorization_rerun_forbidden"] is True
    assert failure.exists()


def test_v180r12r2_verifier_runner_is_producer_free_and_retains_exact_replay() -> None:
    path = ROOT / "scripts/verify_v180r12r2_ten_terminal_aggregation.py"
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        for alias in node.names
    }
    assert not any("finalizer" in name for name in imports)
    assert source.count(
        "verify_ten_terminal_aggregation_independently_v180r12r2("
    ) == 2
    main = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "main"
    )
    first = main.body[0]
    assert isinstance(first, ast.Assign)
    assert 'os.environ[\'ACFQP_V180R12R2_PREREG_COMMIT\']' in ast.unparse(first)
    authorized_try = next(
        node
        for node in main.body
        if isinstance(node, ast.Try)
        and "resource.getrlimit" in ast.unparse(node)
    )
    authorized_source = ast.unparse(authorized_try)
    assert "_read_regular" in authorized_source
    assert "byte_cap=authorization.VERIFICATION_TERMINAL_INPUT_BYTE_CAP" in (
        authorized_source
    )
    assert "resource.setrlimit" in authorized_source
    assert authorized_source.count(
        "_release_transient_heap_and_require_cap_headroom"
    ) == 2
    assert "signal.signal" in authorized_source
    assert "_failure" in authorized_source
    assert "_restore_alarm" in authorized_source
    assert "_suppress_alarm_before_reserve_release" in authorized_source
    assert "_complete_alarm_cleanup_after_reserve_release" in authorized_source
    assert "_alarm_cleanup_observation" in authorized_source
    assert "FAILURE_EMERGENCY_RESERVE_BYTES" in authorized_source
    assert authorized_source.index("_suppress_alarm_before_reserve_release") < (
        authorized_source.index("emergency_failure_reserve.clear")
    ) < authorized_source.index("_complete_alarm_cleanup_after_reserve_release")
    assert "producer-free replay was not exact" in source
    assert "os.O_EXCL" in source
    assert "resource.RLIMIT_AS" in source
    assert "signal.alarm(authorization.TIMEOUT_SECONDS)" in source
    assert source.count("authorization.OUTPUT_TOTAL_BYTE_CAP") >= 3
    assert "verification exceeded its output cap" in source
    assert "verification and replay exceeded their output cap" in source
    freshness = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
        and node.name == "_require_fresh_verification_state"
    )
    freshness_source = ast.unparse(freshness)
    assert "_lexists(VERIFICATION)" in freshness_source
    assert "_lexists(REPLAY)" in freshness_source
    assert "_lexists(RUNTIME_CAS_ROOT)" in freshness_source
    assert "_require_fresh_verification_state()" in ast.unparse(main)
    assert "git push" not in source


@pytest.mark.parametrize("progress_name", ["RUNTIME_CAS_ROOT", "VERIFICATION", "REPLAY"])
def test_v180r12r2_verifier_rejects_any_preexisting_partial_progress(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    progress_name: str,
) -> None:
    runner = _load_runner(
        "verify_v180r12r2_ten_terminal_aggregation.py",
        f"_v180r12r2_verifier_freshness_{progress_name.lower()}",
    )
    terminal = tmp_path / "TERMINAL.json"
    terminal.write_bytes(b"frozen-terminal")
    paths = {
        "TERMINAL": terminal,
        "RUNTIME_CAS_ROOT": tmp_path / "RUNTIME_CAS_ROOT",
        "PRODUCTION_FAILURE": tmp_path / "PRODUCTION_FAILURE.json",
        "FAILURE": tmp_path / "VERIFICATION_FAILURE.json",
        "VERIFICATION": tmp_path / "VERIFICATION.json",
        "REPLAY": tmp_path / "REPLAY.json",
    }
    for name, path in paths.items():
        monkeypatch.setattr(runner, name, path)
    paths[progress_name].write_bytes(b"partial-progress")

    with pytest.raises(
        RuntimeError,
        match="verification input or progress state changed",
    ):
        runner._require_fresh_verification_state()


def test_v180r12r2_verifier_accepts_only_completely_fresh_pair(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runner = _load_runner(
        "verify_v180r12r2_ten_terminal_aggregation.py",
        "_v180r12r2_verifier_fresh_pair",
    )
    terminal = tmp_path / "TERMINAL.json"
    terminal.write_bytes(b"frozen-terminal")
    monkeypatch.setattr(runner, "TERMINAL", terminal)
    monkeypatch.setattr(runner, "RUNTIME_CAS_ROOT", tmp_path / "CAS")
    monkeypatch.setattr(runner, "PRODUCTION_FAILURE", tmp_path / "PF.json")
    monkeypatch.setattr(runner, "FAILURE", tmp_path / "VF.json")
    monkeypatch.setattr(runner, "VERIFICATION", tmp_path / "V.json")
    monkeypatch.setattr(runner, "REPLAY", tmp_path / "R.json")

    runner._require_fresh_verification_state()


@pytest.mark.parametrize("progress_name", ["VERIFICATION", "REPLAY"])
def test_v180r12r2_verification_failure_freezes_partial_progress_bytes(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    progress_name: str,
) -> None:
    runner = _load_runner(
        "verify_v180r12r2_ten_terminal_aggregation.py",
        f"_v180r12r2_verifier_partial_{progress_name.lower()}",
    )
    terminal = tmp_path / "TERMINAL.json"
    verification = tmp_path / "VERIFICATION.json"
    replay = tmp_path / "REPLAY.json"
    failure = tmp_path / "FAILURE.json"
    terminal.write_bytes(b"frozen-terminal")
    paths = {"VERIFICATION": verification, "REPLAY": replay}
    monkeypatch.setattr(runner, "ROOT", tmp_path)
    for name, path in (
        ("TERMINAL", terminal),
        ("PRODUCTION_FAILURE", tmp_path / "PRODUCTION_FAILURE.json"),
        ("FAILURE", failure),
        ("VERIFICATION", verification),
        ("REPLAY", replay),
    ):
        monkeypatch.setattr(runner, name, path)

    target = paths[progress_name]
    partial = f"partial-{progress_name.lower()}".encode("ascii")
    original_write_once = runner._write_once

    def injected_write_once(path: Path, raw: bytes) -> None:
        if path == target:
            path.write_bytes(partial)
            raise OSError("injected post-create write failure")
        original_write_once(path, raw)

    monkeypatch.setattr(runner, "_write_once", injected_write_once)
    try:
        runner._write_once(target, b"complete-progress")
    except OSError as error:
        runner._failure(
            type(error).__name__,
            str(error),
            failure_message_truncated=False,
            alarm_teardown_failure=None,
            authorization_id="a" * 64,
            protocol_id="b" * 64,
            terminal_sha256=hashlib.sha256(b"frozen-terminal").hexdigest(),
        )
    else:  # pragma: no cover - injected failure is deterministic
        raise AssertionError("partial progress injection did not fire")

    document = json.loads(failure.read_bytes())
    key = (
        "verification_output_observation"
        if progress_name == "VERIFICATION"
        else "retained_replay_observation"
    )
    assert document[key] == {
        "state": "PRESENT",
        "byte_count": len(partial),
        "sha256": hashlib.sha256(partial).hexdigest(),
    }
    assert document["partial_progress_bytes_preserved"] is True
    assert document["same_verification_attempt_rerun_forbidden"] is True
    assert failure.exists()


@pytest.mark.parametrize(
    ("filename", "module_name", "helper_name"),
    (
        (
            "run_v180r12r2_ten_terminal_aggregation.py",
            "_v180r12r2_production_heap_release",
            "_release_preexecution_heap_and_require_cap_headroom",
        ),
        (
            "verify_v180r12r2_ten_terminal_aggregation.py",
            "_v180r12r2_verifier_heap_release",
            "_release_transient_heap_and_require_cap_headroom",
        ),
    ),
)
def test_v180r12r2_runners_fail_closed_on_heap_release_contract(
    monkeypatch: pytest.MonkeyPatch,
    filename: str,
    module_name: str,
    helper_name: str,
) -> None:
    runner = _load_runner(filename, module_name)
    assert runner.FAILURE_EMERGENCY_RESERVE_BYTES == (
        runner.authorization.FAILURE_EMERGENCY_RESERVE_BYTES
    )
    assert runner.FAILURE_MESSAGE_BYTE_CAP == (
        runner.authorization.FAILURE_MESSAGE_BYTE_CAP
    )
    assert runner.FAILURE_TYPE_BYTE_CAP == runner.authorization.FAILURE_TYPE_BYTE_CAP
    helper = getattr(runner, helper_name)
    cap = runner.authorization.ADDRESS_SPACE_HARD_CAP_BYTES
    assert 0 < helper(cap) <= cap

    class MissingLibc:
        @property
        def malloc_trim(self):
            raise AttributeError("missing malloc_trim")

    monkeypatch.setattr(runner.ctypes, "CDLL", lambda _name: MissingLibc())
    with pytest.raises(RuntimeError, match="heap release is unavailable"):
        helper(cap)

    class ForeignTrim:
        argtypes = None
        restype = None

        def __call__(self, _padding):
            return 2

    class ForeignLibc:
        malloc_trim = ForeignTrim()

    monkeypatch.setattr(runner.ctypes, "CDLL", lambda _name: ForeignLibc())
    with pytest.raises(RuntimeError, match="foreign status"):
        helper(cap)


@pytest.mark.parametrize(
    "progress_name",
    (
        "OUTPUT_ROOT",
        "RUNTIME_CAS_ROOT",
        "FAILURE",
        "VERIFICATION",
        "VERIFICATION_FAILURE",
        "REPLAY",
    ),
)
def test_v180r12r2_producer_rejects_every_same_authorization_progress_path(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    progress_name: str,
) -> None:
    runner = _load_runner(
        "run_v180r12r2_ten_terminal_aggregation.py",
        f"_v180r12r2_producer_freshness_{progress_name.lower()}",
    )
    paths = {
        name: tmp_path / name
        for name in (
            "OUTPUT_ROOT",
            "RUNTIME_CAS_ROOT",
            "FAILURE",
            "VERIFICATION",
            "VERIFICATION_FAILURE",
            "REPLAY",
        )
    }
    for name, path in paths.items():
        monkeypatch.setattr(runner, name, path)
    paths[progress_name].mkdir()

    with pytest.raises(RuntimeError, match="aggregation already has progress"):
        runner._require_fresh_production_state()


@pytest.mark.parametrize(
    ("filename", "module_name"),
    (
        (
            "run_v180r12r2_ten_terminal_aggregation.py",
            "_v180r12r2_producer_detach_failure",
        ),
        (
            "verify_v180r12r2_ten_terminal_aggregation.py",
            "_v180r12r2_verifier_detach_failure",
        ),
    ),
)
def test_v180r12r2_failure_detaches_large_traceback_locals_and_releases_reserve(
    filename: str,
    module_name: str,
) -> None:
    runner = _load_runner(filename, module_name)

    def fail_with_large_local() -> None:
        retained_large_local = bytearray(2 * 1024 * 1024)
        assert retained_large_local
        raise MemoryError("injected memory pressure")

    try:
        fail_with_large_local()
    except MemoryError as error:
        inner_traceback = error.__traceback__
        assert inner_traceback is not None and inner_traceback.tb_next is not None
        failing_frame = inner_traceback.tb_next.tb_frame
        failure_type, failure_message, truncated = runner._detach_failure(error)
        assert error.__traceback__ is None
    else:  # pragma: no cover - injected failure is deterministic
        raise AssertionError("memory-pressure injection did not fire")

    assert failure_type == "MemoryError"
    assert failure_message == "injected memory pressure"
    assert truncated is False
    assert "retained_large_local" not in failing_frame.f_locals
    reserve = bytearray(runner.FAILURE_EMERGENCY_RESERVE_BYTES)
    runner._release_failure_reserve(reserve)
    assert len(reserve) == 0


def _patch_common_producer_main(
    runner,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    protocol_id = "b" * 64
    authorization_id = "a" * 64
    evidence_id = "c" * 64
    evidence = SimpleNamespace(
        authorization_evidence_id=evidence_id,
        to_document=lambda: {
            "execution_authorization_id": authorization_id,
            "aggregation_protocol_id": protocol_id,
        },
    )
    frozen = SimpleNamespace(
        authorization_id=authorization_id,
        to_document=lambda: {
            "authorization_evidence_verification_is_first_action_inside_runner_"
            "main_after_prelaunch_dispatch": True,
            "authorization_evidence_verification_precedes_scientific_output_"
            "inspection_or_creation_inside_runner": True,
            "authorization_evidence_verification_is_process_first_action": False,
            "prelaunch_contract": {
                "launch_rule_id": (
                    "57e88919b379a3fc2150dcefea46d30488b128832601e31269d225c4de37480b"
                ),
                "production_launch_attempt_relative_path": (
                    ".tmp/exact-freeze/v180r12r2_ten_terminal_aggregation_"
                    "prelaunch/PRODUCTION_LAUNCH_ATTEMPT.json"
                ),
            },
            "aggregation_protocol_id": protocol_id,
        },
    )
    monkeypatch.setenv("ACFQP_V180R12R2_PREREG_COMMIT", "d" * 40)
    monkeypatch.setattr(
        runner.authorization_evidence,
        "freeze_ten_terminal_aggregation_authorization_evidence_v180r12r2",
        lambda *, source_boundary_commit: evidence,
    )
    monkeypatch.setattr(
        runner.authorization,
        "freeze_ten_terminal_aggregation_execution_authorization_v180r12r2",
        lambda: frozen,
    )
    monkeypatch.setattr(runner, "ROOT", tmp_path)
    monkeypatch.setattr(runner, "OUTPUT_ROOT", tmp_path / "output")
    monkeypatch.setattr(runner, "RUNTIME_CAS_ROOT", tmp_path / "cas")
    monkeypatch.setattr(runner, "TERMINAL", tmp_path / "output" / "TERMINAL.json")
    monkeypatch.setattr(runner, "FAILURE", tmp_path / "FAILURE.json")
    monkeypatch.setattr(runner, "VERIFICATION", tmp_path / "VERIFICATION.json")
    monkeypatch.setattr(
        runner,
        "VERIFICATION_FAILURE",
        tmp_path / "VERIFICATION_FAILURE.json",
    )
    monkeypatch.setattr(runner, "REPLAY", tmp_path / "REPLAY.json")
    monkeypatch.setattr(
        runner,
        "_release_preexecution_heap_and_require_cap_headroom",
        lambda _cap: 1,
    )
    monkeypatch.setattr(
        runner.resource,
        "getrlimit",
        lambda _kind: (runner.resource.RLIM_INFINITY, runner.resource.RLIM_INFINITY),
    )
    monkeypatch.setattr(runner.resource, "setrlimit", lambda _kind, _limits: None)
    monkeypatch.setattr(runner.signal, "signal", lambda _kind, _handler: object())
    monkeypatch.setattr(runner.signal, "alarm", lambda _seconds: 0)
    monkeypatch.setattr(
        runner.finalizer,
        "freeze_ten_terminal_aggregation_v180r12r2",
        lambda _root: SimpleNamespace(canonical_bytes=b"{}"),
    )


def test_v180r12r2_producer_teardown_failure_freezes_terminal_and_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runner = _load_runner(
        "run_v180r12r2_ten_terminal_aggregation.py",
        "_v180r12r2_producer_teardown_failure",
    )
    _patch_common_producer_main(runner, monkeypatch, tmp_path)

    def fail_teardown(_handler: object | None, _installed: bool) -> None:
        raise OSError("injected alarm teardown failure")

    monkeypatch.setattr(runner, "_restore_alarm", fail_teardown)
    with pytest.raises(OSError, match="alarm teardown failure"):
        runner.main()

    assert runner.TERMINAL.read_bytes() == b"{}"
    failure = json.loads(runner.FAILURE.read_bytes())
    assert failure["failure_type"] == "OSError"
    assert failure["terminal_output_observation"]["state"] == "PRESENT"
    assert failure["alarm_teardown_failure"]["failure_type"] == "OSError"
    assert failure["same_authorization_rerun_forbidden"] is True


def _patch_common_verifier_main(
    runner,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    protocol_id = "b" * 64
    authorization_id = "a" * 64
    evidence = SimpleNamespace(
        to_document=lambda: {"execution_authorization_id": authorization_id},
    )
    frozen = SimpleNamespace(
        authorization_id=authorization_id,
        to_document=lambda: {
            "authorization_evidence_verification_is_first_action_inside_runner_"
            "main_after_prelaunch_dispatch": True,
            "authorization_evidence_verification_precedes_scientific_output_"
            "inspection_or_creation_inside_runner": True,
            "authorization_evidence_verification_is_process_first_action": False,
            "prelaunch_contract": {
                "launch_rule_id": (
                    "57e88919b379a3fc2150dcefea46d30488b128832601e31269d225c4de37480b"
                ),
                "verification_launch_attempt_relative_path": (
                    ".tmp/exact-freeze/v180r12r2_ten_terminal_aggregation_"
                    "prelaunch/VERIFICATION_LAUNCH_ATTEMPT.json"
                ),
            },
            "aggregation_protocol_id": protocol_id,
        },
    )
    monkeypatch.setenv("ACFQP_V180R12R2_PREREG_COMMIT", "d" * 40)
    monkeypatch.setattr(
        runner.authorization_evidence,
        "freeze_ten_terminal_aggregation_authorization_evidence_v180r12r2",
        lambda *, source_boundary_commit: evidence,
    )
    monkeypatch.setattr(
        runner.authorization,
        "freeze_ten_terminal_aggregation_execution_authorization_v180r12r2",
        lambda: frozen,
    )
    monkeypatch.setattr(runner, "ROOT", tmp_path)
    monkeypatch.setattr(runner, "TERMINAL", tmp_path / "TERMINAL.json")
    monkeypatch.setattr(runner, "RUNTIME_CAS_ROOT", tmp_path / "CAS")
    monkeypatch.setattr(runner, "PRODUCTION_FAILURE", tmp_path / "PF.json")
    monkeypatch.setattr(runner, "VERIFICATION", tmp_path / "VERIFICATION.json")
    monkeypatch.setattr(runner, "FAILURE", tmp_path / "FAILURE.json")
    monkeypatch.setattr(runner, "REPLAY", tmp_path / "REPLAY.json")
    runner.TERMINAL.write_bytes(b"{}")
    monkeypatch.setattr(
        runner,
        "_release_transient_heap_and_require_cap_headroom",
        lambda _cap: 1,
    )
    monkeypatch.setattr(
        runner.resource,
        "getrlimit",
        lambda _kind: (runner.resource.RLIM_INFINITY, runner.resource.RLIM_INFINITY),
    )
    monkeypatch.setattr(runner.resource, "setrlimit", lambda _kind, _limits: None)
    monkeypatch.setattr(runner.signal, "signal", lambda _kind, _handler: object())
    monkeypatch.setattr(runner.signal, "alarm", lambda _seconds: 0)
    monkeypatch.setattr(
        runner.verifier,
        "verify_ten_terminal_aggregation_independently_v180r12r2",
        lambda _raw, _root: {"verification_id": "v" * 64},
    )


def test_v180r12r2_verifier_teardown_failure_freezes_both_outputs_and_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runner = _load_runner(
        "verify_v180r12r2_ten_terminal_aggregation.py",
        "_v180r12r2_verifier_teardown_failure",
    )
    _patch_common_verifier_main(runner, monkeypatch, tmp_path)

    def fail_teardown(_handler: object | None, _installed: bool) -> None:
        raise OSError("injected alarm teardown failure")

    monkeypatch.setattr(runner, "_restore_alarm", fail_teardown)
    with pytest.raises(OSError, match="alarm teardown failure"):
        runner.main()

    assert runner.VERIFICATION.is_file()
    assert runner.REPLAY.is_file()
    failure = json.loads(runner.FAILURE.read_bytes())
    assert failure["failure_type"] == "OSError"
    assert failure["verification_output_observation"]["state"] == "PRESENT"
    assert failure["retained_replay_observation"]["state"] == "PRESENT"
    assert failure["alarm_teardown_failure"]["failure_type"] == "OSError"


@pytest.mark.parametrize(
    ("filename", "module_name"),
    (
        (
            "run_v180r12r2_ten_terminal_aggregation.py",
            "_v180r12r2_producer_hostile_failure_text",
        ),
        (
            "verify_v180r12r2_ten_terminal_aggregation.py",
            "_v180r12r2_verifier_hostile_failure_text",
        ),
    ),
)
def test_v180r12r2_failure_text_bypasses_hostile_str_subclass_encode(
    filename: str,
    module_name: str,
) -> None:
    runner = _load_runner(filename, module_name)

    class HostileText(str):
        def encode(self, *_args, **_kwargs):
            raise MemoryError("injected encode pressure")

    class HostileError(Exception):
        def __str__(self):
            return HostileText("bounded hostile message")

    failure_type, message, truncated = runner._detach_failure(HostileError())
    assert failure_type == "HostileError"
    assert message == "bounded hostile message"
    assert truncated is False
    assert type(message) is str


@pytest.mark.parametrize(
    ("filename", "module_name"),
    (
        (
            "run_v180r12r2_ten_terminal_aggregation.py",
            "_v180r12r2_producer_hostile_failure_metadata",
        ),
        (
            "verify_v180r12r2_ten_terminal_aggregation.py",
            "_v180r12r2_verifier_hostile_failure_metadata",
        ),
    ),
)
def test_v180r12r2_failure_detach_bypasses_hostile_type_and_traceback_access(
    monkeypatch: pytest.MonkeyPatch,
    filename: str,
    module_name: str,
) -> None:
    runner = _load_runner(filename, module_name)

    class HostileMeta(type):
        def __getattribute__(cls, name: str):
            if name == "__name__":
                raise MemoryError("injected hostile type name")
            return super().__getattribute__(name)

    class HostileError(Exception, metaclass=HostileMeta):
        def __getattribute__(self, name: str):
            if name == "__traceback__":
                raise MemoryError("injected hostile traceback read")
            return super().__getattribute__(name)

        def __setattr__(self, name: str, value: object) -> None:
            if name == "__traceback__":
                raise MemoryError("injected hostile traceback write")
            super().__setattr__(name, value)

    try:
        raise HostileError("bounded")
    except HostileError as caught:
        error = caught
    monkeypatch.setattr(
        runner.traceback,
        "clear_frames",
        lambda _traceback: (_ for _ in ()).throw(
            MemoryError("injected clear pressure")
        ),
    )
    failure_type, message, truncated = runner._detach_failure(error)
    assert failure_type == "HostileError"
    assert message == "bounded"
    assert truncated is False


@pytest.mark.parametrize(
    ("filename", "module_name", "observer_name"),
    (
        (
            "run_v180r12r2_ten_terminal_aggregation.py",
            "_v180r12r2_producer_streaming_observation",
            "_terminal_failure_observation",
        ),
        (
            "verify_v180r12r2_ten_terminal_aggregation.py",
            "_v180r12r2_verifier_streaming_observation",
            "_progress_failure_observation",
        ),
    ),
)
def test_v180r12r2_failure_observation_hashes_in_constant_memory(
    filename: str,
    module_name: str,
    observer_name: str,
) -> None:
    runner = _load_runner(filename, module_name)
    source = inspect.getsource(getattr(runner, observer_name))
    assert "digest.update(chunk)" in source
    assert "chunks" not in source
    assert 'b"".join' not in source
    assert "_bounded_failure_text(error)" in source


def test_v180r12r2_verifier_rejects_terminal_before_reading_past_input_cap(
    tmp_path: Path,
) -> None:
    runner = _load_runner(
        "verify_v180r12r2_ten_terminal_aggregation.py",
        "_v180r12r2_verifier_terminal_cap",
    )
    path = tmp_path / "TERMINAL.json"
    path.write_bytes(b"oversized-terminal")
    runner.ROOT = tmp_path
    with pytest.raises(RuntimeError, match="terminal input exceeded its frozen cap"):
        runner._read_regular(path, byte_cap=4)


@pytest.mark.parametrize("runner_kind", ["producer", "verifier"])
def test_v180r12r2_alarm_is_neutralized_before_primary_failure_detach(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    runner_kind: str,
) -> None:
    if runner_kind == "producer":
        runner = _load_runner(
            "run_v180r12r2_ten_terminal_aggregation.py",
            "_v180r12r2_producer_alarm_order",
        )
        _patch_common_producer_main(runner, monkeypatch, tmp_path)

        def fail_scientific_core(_root: Path):
            raise RuntimeError("injected producer failure")

        monkeypatch.setattr(
            runner.finalizer,
            "freeze_ten_terminal_aggregation_v180r12r2",
            fail_scientific_core,
        )
    else:
        runner = _load_runner(
            "verify_v180r12r2_ten_terminal_aggregation.py",
            "_v180r12r2_verifier_alarm_order",
        )
        _patch_common_verifier_main(runner, monkeypatch, tmp_path)

        def fail_scientific_core(_raw: bytes, _root: Path):
            raise RuntimeError("injected verifier failure")

        monkeypatch.setattr(
            runner.verifier,
            "verify_ten_terminal_aggregation_independently_v180r12r2",
            fail_scientific_core,
        )

    state = {"alarm_neutralized": False}
    original_detach = runner._detach_failure

    def record_alarm_cleanup(
        _installed: bool,
    ) -> BaseException | None:
        state["alarm_neutralized"] = True
        return None

    def complete_alarm_cleanup(
        _previous_handler: object | None,
        _installed: bool,
        cleanup_error: BaseException | None,
    ) -> BaseException | None:
        assert state["alarm_neutralized"] is True
        return cleanup_error

    def require_alarm_cleanup(error: BaseException):
        assert state["alarm_neutralized"] is True
        return original_detach(error)

    monkeypatch.setattr(
        runner,
        "_suppress_alarm_before_reserve_release",
        record_alarm_cleanup,
    )
    monkeypatch.setattr(
        runner,
        "_complete_alarm_cleanup_after_reserve_release",
        complete_alarm_cleanup,
    )
    monkeypatch.setattr(runner, "_detach_failure", require_alarm_cleanup)
    with pytest.raises(RuntimeError, match=f"injected {runner_kind} failure"):
        runner.main()
    assert runner.FAILURE.is_file()
