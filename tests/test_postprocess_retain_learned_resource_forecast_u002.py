from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
from types import SimpleNamespace

import pytest

from acfqp.phase3e_ids import canonical_json_bytes
from acfqp.science.learned_resource_forecast_protocol_v1 import (
    build_ratified_learned_resource_forecast_protocol_v1,
)


REPOSITORY = Path(__file__).resolve().parents[1]
POSTPROCESS = (
    REPOSITORY / "scripts/postprocess_retain_learned_resource_forecast_u002.py"
)
PREPARE = REPOSITORY / "scripts/prepare_learned_resource_forecast_campaign_u002.py"
SOURCE_COMMIT = "5" * 40


@pytest.fixture
def linux_tmp_path(request) -> Path:
    path = Path(tempfile.mkdtemp(prefix="acfqp-u002-postprocess-", dir="/tmp"))
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


def _write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json_bytes(value))


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"".join(canonical_json_bytes(row) + b"\n" for row in rows))


def _worker_status_rows(worker: dict, phase: str) -> list[dict]:
    jobs = (
        worker["policy_training_jobs"]
        if phase == "training"
        else worker["player_evidence_jobs"]
    )
    rows = [
        {
            "event": "WORKER_STARTED",
            "phase": phase,
            "worker": worker["worker"],
        }
    ]
    for ordinal, job in enumerate(jobs):
        rows.extend(
            [
                {
                    "event": "JOB_STARTED",
                    "phase": phase,
                    "worker": worker["worker"],
                    "job_ordinal": ordinal,
                    "execution_id": job["execution_id"],
                    "preexecution_identity_check_only": False,
                },
                {
                    "event": "JOB_COMPLETED",
                    "phase": phase,
                    "worker": worker["worker"],
                    "job_ordinal": ordinal,
                    "execution_id": job["execution_id"],
                    "completed_job_count": ordinal + 1,
                    "expected_job_count": len(jobs),
                },
            ]
        )
    rows.append(
        {
            "event": "WORKER_COMPLETED",
            "phase": phase,
            "worker": worker["worker"],
            "completed_job_count": len(jobs),
        }
    )
    return rows


def _dispatch_rows(manifest: dict, phase: str) -> list[dict]:
    fixed = manifest["fixed_paths"]
    rows = [
        {
            "event": "GLOBAL_PRECHECK_COMPLETED",
            "phase": phase,
            "prechecked_worker_count": 6,
            "filesystem_mutation_before_precheck_completed": False,
        },
        {"event": "DISPATCH_STARTED", "phase": phase},
    ]
    for worker in manifest["workers"]:
        status_name = worker[
            "policy_training_status_stream"
            if phase == "training"
            else "player_evidence_status_stream"
        ]
        rows.append(
            {
                "event": "WORKER_DISPATCHED",
                "phase": phase,
                "worker": worker["worker"],
                "host_alias": worker["host_alias"],
                "expected_hostname": worker["expected_hostname"],
                "device": worker["device"],
                "remote_pid": 10_000 + worker["worker"],
                "worker_results_root": str(
                    Path(fixed["results_root"]) / f"worker-{worker['worker']}"
                ),
                "worker_status_stream": str(Path(fixed["status_root"]) / status_name),
                "worker_log": str(
                    Path(fixed["log_root"])
                    / f"worker-{worker['worker']}-{phase}.log"
                ),
            }
        )
    rows.append(
        {
            "event": "DISPATCH_COMPLETED",
            "phase": phase,
            "dispatched_worker_count": 6,
            "worker_execution_completed": False,
        }
    )
    return rows


def _fixture(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    subject = _load(POSTPROCESS, "learned_resource_postprocess_subject")
    prepare = _load(PREPARE, "learned_resource_postprocess_prepare")
    launch_root = tmp_path / "launch"
    _bind_fixed_output_paths(prepare, launch_root)
    protocol = build_ratified_learned_resource_forecast_protocol_v1(SOURCE_COMMIT)
    manifest = prepare.build_launch_manifest_v1(protocol)
    fixed = manifest["fixed_paths"]
    _write_json(Path(fixed["protocol"]), protocol)
    _write_json(Path(fixed["manifest"]), manifest)
    _write_json(Path(fixed["history_scan_receipt"]), {"fixture": True})
    _write_json(Path(fixed["gather_transport_marker"]), {"fixture": True})
    _write_json(Path(fixed["gather_receipt"]), {"fixture": True})

    results_root = Path(fixed["results_root"])
    status_root = Path(fixed["status_root"])
    log_root = Path(fixed["log_root"])
    results_root.mkdir()
    status_root.mkdir()
    log_root.mkdir()
    for worker in manifest["workers"]:
        worker_root = results_root / f"worker-{worker['worker']}"
        worker_root.mkdir()
        for job in worker["policy_training_jobs"]:
            _write_json(worker_root / job["result_filename"], {})
            for filename in job["checkpoint_filenames"]:
                (worker_root / filename).write_bytes(b"model")
        for job in worker["player_evidence_jobs"]:
            _write_json(worker_root / job["label_filename"], {})
            _write_json(worker_root / job["probe_filename"], {})
            if job["split"] == "TRAIN":
                _write_json(worker_root / job["trajectory_metadata_filename"], {})
                (worker_root / job["trajectory_array_filename"]).write_bytes(b"npz")
        for phase, status_key in (
            ("training", "policy_training_status_stream"),
            ("evidence", "player_evidence_status_stream"),
        ):
            _write_jsonl(
                status_root / worker[status_key],
                _worker_status_rows(worker, phase),
            )
            _write_jsonl(
                log_root / f"worker-{worker['worker']}-{phase}.log",
                [
                    {
                        "success": True,
                        "phase": phase,
                        "worker": worker["worker"],
                        "completed_job_count": 24 if phase == "training" else 72,
                        "results_root": str(worker_root),
                    }
                ],
            )
    for phase, key in (
        ("training", "training_dispatch_status"),
        ("evidence", "evidence_dispatch_status"),
    ):
        _write_jsonl(Path(fixed[key]), _dispatch_rows(manifest, phase))

    monkeypatch.setattr(subject, "_load_prepare_module", lambda: prepare)
    monkeypatch.setattr(
        subject,
        "_load_history_scan_module",
        lambda: SimpleNamespace(
            validate_history_scan_receipt_v1=lambda receipt, protocol, manifest: receipt
        ),
    )
    monkeypatch.setattr(
        subject,
        "_load_gather_module",
        lambda: SimpleNamespace(
            validate_gather_receipt_v1=lambda receipt, protocol, manifest: receipt
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
    monkeypatch.setattr(
        subject,
        "_default_runtime_validator",
        lambda protocol_path, manifest_path, device: None,
    )
    args = SimpleNamespace(
        protocol=Path(fixed["protocol"]),
        manifest=Path(fixed["manifest"]),
        history_scan_receipt=Path(fixed["history_scan_receipt"]),
        gather_receipt=Path(fixed["gather_receipt"]),
        analysis_device=manifest["central_analysis"]["device"],
        verifier_device=manifest["central_analysis"]["device"],
    )
    return subject, protocol, manifest, args


def _mock_runners(manifest: dict, calls: list[str]):
    analysis_root = Path(manifest["fixed_paths"]["analysis_root"])

    def analysis_runner(args: SimpleNamespace) -> dict:
        calls.append(args.operation)
        if args.operation == "fit-encoders":
            for name in (
                "aligned-resource-forecast.encoder.pt",
                "player-shuffled-resource-forecast.encoder.pt",
                "aligned-resource-forecast.receipt.json",
                "player-shuffled-resource-forecast.receipt.json",
            ):
                (analysis_root / name).write_bytes(b"fit")
        elif args.operation == "encode-probes":
            (analysis_root / "probe-representation-matrices.npz").write_bytes(b"matrix")
            _write_json(
                analysis_root / "probe-representation-matrices.metadata.json", {}
            )
        elif args.operation == "evaluate":
            _write_json(
                analysis_root / "pilot-result.json",
                {"PROVISIONAL_DESIGN_SIGNAL_GATE": "PASS"},
            )
        return {"success": True}

    def verifier_runner(_args: SimpleNamespace) -> dict:
        calls.append("independent-verifier")
        _write_json(
            analysis_root / "independent-verification.json", {"valid": True}
        )
        return {"success": True, "valid": True}

    return analysis_runner, verifier_runner


def test_one_shot_postprocess_runs_in_order_and_retains_exact_inventory(
    linux_tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    subject, _protocol, manifest, args = _fixture(linux_tmp_path, monkeypatch)
    calls: list[str] = []
    analysis_runner, verifier_runner = _mock_runners(manifest, calls)

    summary = subject._run(
        args, analysis_runner=analysis_runner, verifier_runner=verifier_runner
    )

    assert calls == [
        "fit-encoders",
        "encode-probes",
        "evaluate",
        "independent-verifier",
    ]
    assert summary["success"] is True
    assert summary["PROVISIONAL_DESIGN_SIGNAL_GATE"] == "PASS"
    assert summary["independent_verification"] is True
    assert summary["retained_artifact_count_excluding_inventory"] == 2056
    assert summary["physical_file_count_including_inventory"] == 2057
    retained = Path(manifest["fixed_paths"]["retained_root"])
    inventory = json.loads(
        (retained / "retention-inventory.json").read_text(encoding="utf-8")
    )
    assert inventory["category_counts"] == subject.EXPECTED_CATEGORY_COUNTS_V1
    assert len(inventory["entries"]) == 2056
    assert len([path for path in retained.rglob("*") if path.is_file()]) == 2057
    events = [
        json.loads(line)
        for line in Path(manifest["fixed_paths"]["postprocess_status"])
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    assert events[-1]["event"] == (
        "ANALYSIS_VERIFICATION_COMPLETED_RETENTION_READY"
    )
    assert events[-1]["retention_complete"] is False
    retained_status = retained / "status/postprocess-status.jsonl"
    assert retained_status.read_bytes() == Path(
        manifest["fixed_paths"]["postprocess_status"]
    ).read_bytes()


def test_foreign_worker_artifact_fails_before_any_analysis_stage(
    linux_tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    subject, _protocol, manifest, args = _fixture(linux_tmp_path, monkeypatch)
    foreign = Path(manifest["fixed_paths"]["results_root"]) / "worker-0/foreign.txt"
    foreign.write_text("foreign", encoding="utf-8")
    calls: list[str] = []

    with pytest.raises(
        subject.LearnedResourceForecastPostprocessV1Error,
        match="missing, duplicate, foreign",
    ):
        subject._run(
            args,
            analysis_runner=lambda stage_args: calls.append(stage_args.operation),
            verifier_runner=lambda verifier_args: calls.append("verifier"),
        )

    assert calls == []
    assert not Path(manifest["fixed_paths"]["analysis_root"]).exists()
    assert not Path(manifest["fixed_paths"]["retained_root"]).exists()
    status = Path(manifest["fixed_paths"]["postprocess_status"])
    assert not status.exists()


def test_failed_first_stage_stops_later_stages_and_consumes_attempt(
    linux_tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    subject, _protocol, manifest, args = _fixture(linux_tmp_path, monkeypatch)
    calls: list[str] = []

    def failed_stage(stage_args: SimpleNamespace) -> dict:
        calls.append(stage_args.operation)
        raise RuntimeError("synthetic fit failure")

    with pytest.raises(RuntimeError, match="synthetic fit failure"):
        subject._run(
            args,
            analysis_runner=failed_stage,
            verifier_runner=lambda verifier_args: calls.append("verifier"),
        )
    assert calls == ["fit-encoders"]
    assert not Path(manifest["fixed_paths"]["retained_root"]).exists()
    with pytest.raises(
        subject.LearnedResourceForecastPostprocessV1Error,
        match="attempt is consumed",
    ):
        subject._run(args, analysis_runner=failed_stage)


def test_failure_after_status_close_never_claims_retention_complete(
    linux_tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    subject, _protocol, manifest, args = _fixture(linux_tmp_path, monkeypatch)
    calls: list[str] = []
    analysis_runner, verifier_runner = _mock_runners(manifest, calls)

    def failed_retention(**_kwargs):
        raise RuntimeError("synthetic closed-status copy failure")

    with pytest.raises(RuntimeError, match="closed-status copy failure"):
        subject._run(
            args,
            analysis_runner=analysis_runner,
            verifier_runner=verifier_runner,
            retention_copier=failed_retention,
        )

    status = Path(manifest["fixed_paths"]["postprocess_status"])
    rows = [json.loads(line) for line in status.read_text(encoding="utf-8").splitlines()]
    assert rows[-1]["event"] == (
        "ANALYSIS_VERIFICATION_COMPLETED_RETENTION_READY"
    )
    assert rows[-1]["retention_complete"] is False
    assert all(row.get("retention_complete") is not True for row in rows)
    retained = Path(manifest["fixed_paths"]["retained_root"])
    assert not (retained / "retention-inventory.json").exists()
