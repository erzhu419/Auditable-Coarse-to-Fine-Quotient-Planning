from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from acfqp.phase3e_ids import canonical_json_bytes
from acfqp.science.learned_resource_forecast_protocol_v1 import (
    build_ratified_learned_resource_forecast_protocol_v1,
)


REPOSITORY = Path(__file__).resolve().parents[1]
LAUNCHER = REPOSITORY / "scripts/launch_learned_resource_forecast_campaign_u001.py"
PREPARE = REPOSITORY / "scripts/prepare_learned_resource_forecast_campaign_u001.py"
SOURCE_COMMIT = "9" * 40


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _bind_fixed_output_paths(module, root: Path) -> None:
    module.FIXED_LAUNCH_ROOT = root
    module.FIXED_RESULTS_ROOT = root.parent / "results"
    module.FIXED_STATUS_ROOT = root.parent / "status"
    module.FIXED_LOG_ROOT = root.parent / "logs"
    module.FIXED_ANALYSIS_ROOT = root.parent / "analysis"
    module.FIXED_RETAINED_ROOT = root.parent / "retained"
    module.FIXED_PROTOCOL_PATH = root / "protocol.json"
    module.FIXED_MANIFEST_PATH = root / "launch-manifest.json"
    module.FIXED_HISTORY_SCAN_RECEIPT_PATH = root / "history-scan-receipt.json"
    module.FIXED_GATHER_TRANSPORT_MARKER_PATH = root / "gather-transport-marker.json"
    module.FIXED_GATHER_RECEIPT_PATH = root / "gather-receipt.json"
    module.FIXED_TRAINING_DISPATCH_STATUS_PATH = root / "training-dispatch.jsonl"
    module.FIXED_EVIDENCE_DISPATCH_STATUS_PATH = root / "evidence-dispatch.jsonl"
    module.FIXED_POSTPROCESS_STATUS_PATH = root / "postprocess-status.jsonl"


def _fixture(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, phase: str):
    launcher = _load(LAUNCHER, "learned_resource_launcher_test_subject")
    prepare = _load(PREPARE, "learned_resource_launcher_prepare_helper")
    launch_root = tmp_path / "launch"
    _bind_fixed_output_paths(prepare, launch_root)
    protocol = build_ratified_learned_resource_forecast_protocol_v1(SOURCE_COMMIT)
    manifest = prepare.build_launch_manifest_v1(protocol)
    protocol_path = launch_root / "protocol.json"
    manifest_path = launch_root / "launch-manifest.json"
    history_receipt_path = launch_root / "history-scan-receipt.json"
    protocol_path.parent.mkdir(parents=True)
    protocol_path.write_bytes(canonical_json_bytes(protocol))
    manifest_path.write_bytes(canonical_json_bytes(manifest))
    history_receipt_path.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(
        launcher,
        "bound_clean_source_commit_v1",
        lambda _repository: SOURCE_COMMIT,
    )
    monkeypatch.setattr(launcher, "_load_prepare_module", lambda: prepare)
    monkeypatch.setattr(
        launcher,
        "_load_history_scan_module",
        lambda: SimpleNamespace(
            validate_history_scan_receipt_v1=lambda receipt, protocol, manifest: receipt
        ),
    )
    monkeypatch.setattr(
        launcher,
        "_load_postprocess_module",
        lambda: SimpleNamespace(
            _validate_dispatch_status=lambda path, phase, manifest, fixed: None
        ),
    )
    args = SimpleNamespace(
        phase=phase,
        protocol=protocol_path,
        manifest=manifest_path,
        history_scan_receipt=history_receipt_path,
        remote_results_root=Path(manifest["fixed_paths"]["results_root"]),
        remote_status_root=Path(manifest["fixed_paths"]["status_root"]),
        remote_log_root=Path(manifest["fixed_paths"]["log_root"]),
        dispatch_status=Path(
            manifest["fixed_paths"][f"{phase}_dispatch_status"]
        ),
    )
    return launcher, protocol, manifest, args


def _events(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def _successful_global_preflight(manifest: dict, phase: str, calls: list):
    def run(host_alias: str, command: str) -> dict:
        worker = manifest["workers"][len(calls)]
        calls.append((host_alias, command))
        return {
            "success": True,
            "global_preflight_only": True,
            "filesystem_mutation": False,
            "phase": phase,
            "worker": worker["worker"],
            "source_commit": manifest["source_commit"],
            "protocol_id": manifest["protocol_id"],
        }

    return run


@pytest.mark.parametrize("phase", ["training", "evidence"])
def test_launcher_dispatches_six_manifest_workers_with_exact_source_pythonpath(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, phase: str
) -> None:
    launcher, _protocol, manifest, args = _fixture(
        tmp_path, monkeypatch, phase
    )
    calls = []
    preflight_calls = []

    def dispatcher(host_alias: str, command: str) -> str:
        calls.append((host_alias, command))
        return str(10_000 + len(calls))

    summary = launcher._launch(
        args,
        dispatcher=dispatcher,
        global_preflight=_successful_global_preflight(
            manifest, phase, preflight_calls
        ),
    )
    events = _events(args.dispatch_status)

    assert summary["dispatched_worker_count"] == len(calls) == 6
    assert len(preflight_calls) == 6
    assert all("--global-preflight-only" in command for _host, command in preflight_calls)
    assert all(
        "mkdir" not in command and "nohup" not in command and ">" not in command
        for _host, command in preflight_calls
    )
    assert summary["worker_execution_completed"] is False
    assert [host for host, _command in calls] == [
        worker["host_alias"] for worker in manifest["workers"]
    ]
    for worker, (_host, command) in zip(
        manifest["workers"], calls, strict=True
    ):
        assert "nohup" in command
        assert "--preflight-only > /dev/null; nohup" in command
        assert f"PYTHONPATH={manifest['source_pythonpath']}" in command
        assert worker["python"] in command
        assert (
            f"{manifest['source_checkout']}/scripts/"
            "run_learned_resource_forecast_worker_u001.py"
        ) in command
        assert f"--worker {worker['worker']}" in command
        assert f"--phase {phase}" in command
        assert f"--device {worker['device']}" in command
        assert (
            f"--results-root {args.remote_results_root}/"
            f"worker-{worker['worker']}"
        ) in command
        worker_root = (
            f"{args.remote_results_root}/worker-{worker['worker']}"
        )
        if phase == "training":
            assert f"test ! -e {worker_root}" in command
            assert f"mkdir {worker_root}" in command
            assert f"mkdir -p {worker_root} " not in command
        else:
            assert f"test -d {worker_root}" in command
            assert f"mkdir {worker_root}" not in command
    assert len(
        {row["worker_results_root"] for row in summary["workers"]}
    ) == 6
    assert [row["worker_results_root"] for row in summary["workers"]] == [
        str(args.remote_results_root / f"worker-{index}")
        for index in range(6)
    ]
    assert events[0]["event"] == "GLOBAL_PRECHECK_COMPLETED"
    assert events[1]["event"] == "DISPATCH_STARTED"
    assert sum(event["event"] == "WORKER_DISPATCHED" for event in events) == 6
    assert events[-1]["event"] == "DISPATCH_COMPLETED"
    assert events[-1]["worker_execution_completed"] is False


def test_first_dispatch_failure_stops_remaining_workers_and_is_retained(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    launcher, _protocol, manifest, args = _fixture(
        tmp_path, monkeypatch, "training"
    )
    calls = []
    preflight_calls = []

    def dispatcher(host_alias: str, command: str) -> str:
        calls.append((host_alias, command))
        if len(calls) == 3:
            raise RuntimeError("synthetic dispatch failure")
        return str(20_000 + len(calls))

    with pytest.raises(RuntimeError, match="synthetic dispatch failure"):
        launcher._launch(
            args,
            dispatcher=dispatcher,
            global_preflight=_successful_global_preflight(
                manifest, "training", preflight_calls
            ),
        )
    events = _events(args.dispatch_status)

    assert len(calls) == 3
    assert [host for host, _command in calls] == [
        worker["host_alias"] for worker in manifest["workers"][:3]
    ]
    assert [event["event"] for event in events] == [
        "GLOBAL_PRECHECK_COMPLETED",
        "DISPATCH_STARTED",
        "WORKER_DISPATCHED",
        "WORKER_DISPATCHED",
        "WORKER_DISPATCH_FAILED",
        "DISPATCH_FAILED",
    ]


def test_existing_dispatch_status_forbids_any_second_dispatch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    launcher, _protocol, _manifest, args = _fixture(
        tmp_path, monkeypatch, "training"
    )
    args.dispatch_status.write_text("retained launch attempt\n", encoding="utf-8")
    calls = []

    with pytest.raises(
        launcher.LearnedResourceForecastLauncherV1Error,
        match="launch identity is consumed",
    ):
        launcher._launch(
            args,
            dispatcher=lambda host, command: calls.append((host, command)),
            global_preflight=lambda host, command: (_ for _ in ()).throw(
                AssertionError("preflight must not run after identity consumption")
            ),
        )
    assert calls == []
    assert args.dispatch_status.read_text(encoding="utf-8") == (
        "retained launch attempt\n"
    )


def test_unclosed_evidence_global_preflight_starts_no_worker_and_writes_no_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    launcher, _protocol, manifest, args = _fixture(
        tmp_path, monkeypatch, "evidence"
    )
    preflight_calls = []
    dispatch_calls = []

    def fail_last(host_alias: str, command: str) -> dict:
        worker = manifest["workers"][len(preflight_calls)]
        preflight_calls.append((host_alias, command))
        if worker["worker"] == 5:
            raise RuntimeError("synthetic worker-5 training status unclosed")
        return {
            "success": True,
            "global_preflight_only": True,
            "filesystem_mutation": False,
            "phase": "evidence",
            "worker": worker["worker"],
            "source_commit": manifest["source_commit"],
            "protocol_id": manifest["protocol_id"],
        }

    with pytest.raises(RuntimeError, match="training status unclosed"):
        launcher._launch(
            args,
            dispatcher=lambda host, command: dispatch_calls.append((host, command)),
            global_preflight=fail_last,
        )
    assert len(preflight_calls) == 6
    assert dispatch_calls == []
    assert not args.dispatch_status.exists()


def test_ssh_dispatch_rejects_preflight_output_mixed_with_pid(monkeypatch) -> None:
    launcher = _load(LAUNCHER, "learned_resource_launcher_pid_subject")
    monkeypatch.setattr(
        launcher.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(
            returncode=0, stdout='{"preflight_only": true}\n12345\n', stderr=""
        ),
    )
    with pytest.raises(
        launcher.LearnedResourceForecastLauncherV1Error,
        match="returned no exact worker PID",
    ):
        launcher._ssh_dispatch("fixture-host", "fixture-command")
