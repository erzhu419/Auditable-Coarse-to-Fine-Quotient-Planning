from __future__ import annotations

import importlib.util
import io
from pathlib import Path
import shutil
import shlex
import tempfile
from types import SimpleNamespace

import pytest

from acfqp.phase3e_ids import canonical_json_bytes
from acfqp.science.learned_resource_forecast_protocol_v1 import (
    build_ratified_learned_resource_forecast_protocol_v1,
)


REPOSITORY = Path(__file__).resolve().parents[1]
GATHER = REPOSITORY / "scripts/gather_learned_resource_forecast_evidence_u002.py"
PREPARE = REPOSITORY / "scripts/prepare_learned_resource_forecast_campaign_u002.py"
SOURCE_COMMIT = "4" * 40


@pytest.fixture
def linux_tmp_path(request) -> Path:
    path = Path(tempfile.mkdtemp(prefix="acfqp-u002-gather-", dir="/tmp"))
    request.addfinalizer(lambda: shutil.rmtree(path, ignore_errors=True))
    return path


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


def _fixture(linux_tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    subject = _load(GATHER, "learned_resource_gather_subject")
    prepare = _load(PREPARE, "learned_resource_gather_prepare")
    launch = linux_tmp_path / "launch"
    _bind_fixed_output_paths(prepare, launch)
    protocol = build_ratified_learned_resource_forecast_protocol_v1(SOURCE_COMMIT)
    manifest = prepare.build_launch_manifest_v1(protocol)
    fixed = manifest["fixed_paths"]
    launch.mkdir()
    Path(fixed["protocol"]).write_bytes(canonical_json_bytes(protocol))
    Path(fixed["manifest"]).write_bytes(canonical_json_bytes(manifest))
    Path(fixed["history_scan_receipt"]).write_text("{}", encoding="utf-8")
    Path(fixed["training_dispatch_status"]).write_text("fixture\n", encoding="utf-8")
    Path(fixed["evidence_dispatch_status"]).write_text("fixture\n", encoding="utf-8")
    Path(fixed["results_root"]).mkdir()
    Path(fixed["status_root"]).mkdir()
    Path(fixed["log_root"]).mkdir()
    monkeypatch.setattr(subject, "_load_prepare_module", lambda: prepare)
    monkeypatch.setattr(
        subject,
        "_load_history_scan_module",
        lambda: SimpleNamespace(
            validate_history_scan_receipt_v1=lambda receipt, protocol, manifest: receipt
        ),
    )
    monkeypatch.setattr(
        subject, "bound_clean_source_commit_v1", lambda _repository: SOURCE_COMMIT
    )
    monkeypatch.setattr(
        subject.socket,
        "gethostname",
        lambda: manifest["central_analysis"]["expected_hostname"],
    )
    common = subject._common_root(manifest)
    host_map = {
        row["host_alias"]: row for row in subject._host_workers(manifest)
    }

    def inspector(host_alias: str, request: dict) -> dict:
        expected = host_map[host_alias]
        files = [
            {
                "relative_path": path.resolve().relative_to(common).as_posix(),
                "size_bytes": 1,
            }
            for index in expected["workers"]
            for path in subject._worker_file_paths(manifest, index)
        ]
        return {
            "actual_hostname": expected["expected_hostname"],
            "workers": expected["workers"],
            "files": files,
            "job_reexecution": False,
        }

    def transport(_host_alias: str, request: dict) -> None:
        for row in request["files"]:
            target = common / row["relative_path"]
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(b"x")

    def central_inspector(_host_alias: str, request: dict) -> dict:
        state = request["state"]
        remote_dirs = [
            Path(manifest["fixed_paths"]["results_root"]) / f"worker-{index}"
            for index in subject.REMOTE_WORKERS_V1
        ]
        if state == "FIRST" and any(path.exists() for path in remote_dirs):
            raise subject.LearnedResourceForecastGatherV1Error(
                "remote-worker gather destination exists before first transport"
            )
        files = [
            {
                "relative_path": path.resolve().relative_to(common).as_posix(),
                "size_bytes": path.stat().st_size,
            }
            for index in subject.REMOTE_WORKERS_V1
            for path in subject._worker_file_paths(manifest, index)
            if path.is_file()
        ]
        return {
            "actual_hostname": manifest["central_analysis"]["expected_hostname"],
            "state": state,
            "files": files,
            "job_reexecution": False,
        }

    return subject, protocol, manifest, inspector, transport, central_inspector


def test_gather_streams_only_remote_workers_and_writes_exclusive_receipt(
    linux_tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    subject, protocol, manifest, inspector, transport, central_inspector = _fixture(
        linux_tmp_path, monkeypatch
    )
    fixed = manifest["fixed_paths"]
    calls: list[str] = []

    def recording_transport(host: str, request: dict) -> None:
        calls.append(host)
        transport(host, request)

    receipt = subject._gather(
        protocol_path=Path(fixed["protocol"]),
        manifest_path=Path(fixed["manifest"]),
        history_path=Path(fixed["history_scan_receipt"]),
        inspector=inspector,
        transporter=recording_transport,
        central_inspector=central_inspector,
        small_file_copier=lambda host, path, raw, python: None,
    )

    assert calls == ["jtl110gpu", "jtl311linux"]
    assert receipt["remote_workers"] == [2, 3, 4, 5]
    assert receipt["job_reexecution"] is False
    assert receipt["transport_method"] == (
        "LOCAL_CONTROLLER_SSH_SOURCE_TAR_STDOUT_TO_SSH_GPU2_TAR_STDIN"
    )
    assert Path(fixed["gather_transport_marker"]).is_file()
    assert Path(fixed["gather_receipt"]).is_file()
    assert subject.validate_gather_receipt_v1(receipt, protocol, manifest) == receipt


def test_interrupted_transport_retries_only_evidence_copy_and_never_jobs(
    linux_tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    subject, _protocol, manifest, inspector, transport, central_inspector = _fixture(
        linux_tmp_path, monkeypatch
    )
    fixed = manifest["fixed_paths"]
    attempts = 0

    def fail_once(host: str, request: dict) -> None:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            for row in request["files"][:10]:
                target = subject._common_root(manifest) / row["relative_path"]
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(b"x")
            raise RuntimeError("synthetic transport interruption")
        transport(host, request)

    with pytest.raises(RuntimeError, match="synthetic transport interruption"):
        subject._gather(
            protocol_path=Path(fixed["protocol"]),
            manifest_path=Path(fixed["manifest"]),
            history_path=Path(fixed["history_scan_receipt"]),
            inspector=inspector,
            transporter=fail_once,
            central_inspector=central_inspector,
            small_file_copier=lambda host, path, raw, python: None,
        )
    assert Path(fixed["gather_transport_marker"]).is_file()
    assert not Path(fixed["gather_receipt"]).exists()

    receipt = subject._gather(
        protocol_path=Path(fixed["protocol"]),
        manifest_path=Path(fixed["manifest"]),
        history_path=Path(fixed["history_scan_receipt"]),
        inspector=inspector,
        transporter=fail_once,
        central_inspector=central_inspector,
        small_file_copier=lambda host, path, raw, python: None,
    )
    assert receipt["job_reexecution"] is False
    assert attempts == 3


def test_first_gather_rejects_preexisting_remote_worker_destination(
    linux_tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    subject, _protocol, manifest, inspector, transport, central_inspector = _fixture(
        linux_tmp_path, monkeypatch
    )
    fixed = manifest["fixed_paths"]
    (Path(fixed["results_root"]) / "worker-2").mkdir()
    calls: list[str] = []
    with pytest.raises(
        subject.LearnedResourceForecastGatherV1Error,
        match="destination exists before first transport",
    ):
        subject._gather(
            protocol_path=Path(fixed["protocol"]),
            manifest_path=Path(fixed["manifest"]),
            history_path=Path(fixed["history_scan_receipt"]),
            inspector=inspector,
            transporter=lambda host, request: calls.append(host),
            central_inspector=central_inspector,
            small_file_copier=lambda host, path, raw, python: None,
        )
    assert calls == []
    assert not Path(fixed["gather_transport_marker"]).exists()


def test_transport_is_direct_source_ssh_stdout_to_gpu2_ssh_stdin(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    subject = _load(GATHER, "learned_resource_gather_topology_subject")
    calls = []

    class FakeSourceProcess:
        def __init__(self, arguments, **_kwargs):
            calls.append(("source", arguments))
            self.stdout = io.BytesIO(b"tar-stream")
            self.stderr = io.BytesIO(b"")

        def wait(self):
            return 0

    def fake_run(arguments, **kwargs):
        calls.append(("central", arguments, kwargs["stdin"]))
        return SimpleNamespace(returncode=0, stderr=b"")

    monkeypatch.setattr(subject.subprocess, "Popen", FakeSourceProcess)
    monkeypatch.setattr(subject.subprocess, "run", fake_run)
    subject._tar_stream_transport(
        "jtl110gpu",
        {
            "common_root": "/home/erzhu419/mine_code",
            "tar_members": ["results/worker-2"],
            "central_host_alias": "jtl110gpu2",
        },
    )

    assert calls[0][1][:4] == ["ssh", "-o", "BatchMode=yes", "jtl110gpu"]
    assert calls[1][1][:4] == ["ssh", "-o", "BatchMode=yes", "jtl110gpu2"]
    assert calls[1][2] is not None
    assert all(arguments[0] != "tar" for _kind, arguments, *rest in calls)


def test_small_authority_python_program_is_one_shell_quoted_remote_command(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    subject = _load(GATHER, "learned_resource_gather_small_copy_subject")
    captured = {}

    def fake_run(arguments, **kwargs):
        captured["arguments"] = arguments
        captured["input"] = kwargs["input"]
        return SimpleNamespace(returncode=0, stderr=b"")

    monkeypatch.setattr(subject.subprocess, "run", fake_run)
    subject._copy_small_to_remote(
        "jtl110gpu2",
        Path("/home/erzhu419/mine_code/u002 launch/receipt.json"),
        b'{"ok":true}',
        "/home/erzhu419/.venvs/runtime/bin/python",
    )

    arguments = captured["arguments"]
    assert arguments[:4] == ["ssh", "-o", "BatchMode=yes", "jtl110gpu2"]
    assert len(arguments) == 5
    remote = shlex.split(arguments[4])
    assert remote[0] == "/home/erzhu419/.venvs/runtime/bin/python"
    assert remote[1] == "-c"
    assert "os.O_EXCL" in remote[2]
    assert remote[3] == "/home/erzhu419/mine_code/u002 launch/receipt.json"
    assert captured["input"] == b'{"ok":true}'
