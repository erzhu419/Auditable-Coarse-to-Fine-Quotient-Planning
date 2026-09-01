from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from acfqp.phase3e_ids import canonical_json_bytes
from acfqp.science.learned_resource_forecast_evidence_v1 import (
    LABEL_EVIDENCE_SCHEMA_V1,
    PROBE_EVIDENCE_SCHEMA_V1,
    TRAJECTORY_EVIDENCE_SCHEMA_V1,
)
from acfqp.science.learned_resource_forecast_protocol_v1 import (
    build_ratified_learned_resource_forecast_protocol_v1,
)
from acfqp.science.matched_double_dqn_2048_learned_resource_pilot_v1 import (
    LEARNED_RESOURCE_POLICY_TRAINING_RESULT_SCHEMA_V1,
)


REPOSITORY = Path(__file__).resolve().parents[1]
WORKER_SCRIPT = REPOSITORY / "scripts/run_learned_resource_forecast_worker_u001.py"
PREPARE_SCRIPT = (
    REPOSITORY / "scripts/prepare_learned_resource_forecast_campaign_u001.py"
)
SOURCE_COMMIT = "8" * 40


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _modules():
    return (
        _load(WORKER_SCRIPT, "learned_resource_worker_test_subject"),
        _load(PREPARE_SCRIPT, "learned_resource_prepare_test_helper"),
    )


def _write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json_bytes(value))


def _bind_manifest_paths(
    manifest: dict, *, launch_root: Path, worker_root: Path, status_root: Path
) -> None:
    fixed = manifest["fixed_paths"]
    fixed.update(
        {
            "launch_root": str(launch_root),
            "protocol": str(launch_root / "protocol.json"),
            "manifest": str(launch_root / "launch-manifest.json"),
            "history_scan_receipt": str(launch_root / "history-scan-receipt.json"),
            "results_root": str(worker_root.parent),
            "status_root": str(status_root),
            "log_root": str(launch_root.parent / "logs"),
            "analysis_root": str(launch_root.parent / "analysis"),
            "retained_root": str(launch_root.parent / "retained"),
            "training_dispatch_status": str(launch_root / "training-dispatch.jsonl"),
            "evidence_dispatch_status": str(launch_root / "evidence-dispatch.jsonl"),
            "postprocess_status": str(launch_root / "postprocess-status.jsonl"),
        }
    )


def _fixture(tmp_path: Path, *, phase: str, worker_index: int = 0):
    subject, prepare = _modules()
    protocol = build_ratified_learned_resource_forecast_protocol_v1(SOURCE_COMMIT)
    manifest = prepare.build_launch_manifest_v1(protocol)
    protocol_path = tmp_path / "launch" / "protocol.json"
    manifest_path = tmp_path / "launch" / "launch-manifest.json"
    results_root = tmp_path / "results" / f"worker-{worker_index}"
    worker = manifest["workers"][worker_index]
    status_name = (
        worker["policy_training_status_stream"]
        if phase == "training"
        else worker["player_evidence_status_stream"]
    )
    status_root = tmp_path / "status"
    status = status_root / status_name
    _bind_manifest_paths(
        manifest,
        launch_root=protocol_path.parent,
        worker_root=results_root,
        status_root=status_root,
    )
    subject._expected_manifest = lambda _protocol: manifest
    results_root.mkdir(parents=True)
    _write_json(protocol_path, protocol)
    _write_json(manifest_path, manifest)
    args = SimpleNamespace(
        worker=worker_index,
        phase=phase,
        protocol=protocol_path,
        manifest=manifest_path,
        results_root=results_root,
        status_stream=status,
        device=worker["device"],
        preflight_only=False,
    )
    return subject, protocol, manifest, worker, args


def _bind_runtime(subject, manifest: dict, worker: dict, monkeypatch) -> None:
    monkeypatch.setattr(
        subject, "bound_clean_source_commit_v1", lambda _repository: SOURCE_COMMIT
    )
    required = manifest["required_runtime"]
    monkeypatch.setattr(
        subject,
        "_actual_runtime_context",
        lambda device: {
            "hostname": worker["expected_hostname"],
            "python_version": required["python_version"],
            "python_path": worker["python"],
            "pythonpath_environment": manifest["source_pythonpath"],
            "sys_path": [
                str(REPOSITORY / "scripts"),
                manifest["source_pythonpath"],
            ],
            "acfqp_file": str(REPOSITORY / "src/acfqp/__init__.py"),
            "numpy_version": required["numpy_version"],
            "scipy_version": required["scipy_version"],
            "torch_version": required["torch_version"],
            "torch_cuda_runtime_version": required["torch_cuda_runtime_version"],
            "torch_cudnn_version": 90100,
            "device": device,
            "cuda_device_name": "fixture GPU",
        },
    )


def _training_result(
    protocol: dict, worker: dict, job: dict, root: Path
) -> dict:
    checkpoint_rows = [
        {
            "checkpoint_environment_interactions": checkpoint,
            "filename": filename,
            "artifact_kind": "INFERENCE_ONLY_BARE_ONLINE_STATE_DICT",
        }
        for checkpoint, filename in zip(
            protocol["training"]["evaluation_checkpoints"],
            job["checkpoint_filenames"],
            strict=True,
        )
    ]
    result_path = root / job["result_filename"]
    result = {
        "schema": LEARNED_RESOURCE_POLICY_TRAINING_RESULT_SCHEMA_V1,
        "protocol_id": protocol["protocol_id"],
        "arm": job["arm"],
        "seed": job["seed"],
        "device": worker["device"],
        "execution_context": {
            "execution_id": job["execution_id"],
            "source_commit": protocol["source_commit"],
            "hostname": worker["expected_hostname"],
            "device": worker["device"],
        },
        "artifact_manifest": {
            "result_filename": job["result_filename"],
            "checkpoint_files": checkpoint_rows,
            "checkpoint_file_count": 3,
            "separate_final_model_artifact_written": False,
        },
    }
    _write_json(result_path, result)
    for filename in job["checkpoint_filenames"]:
        (root / filename).write_bytes(b"bare-state-dict-fixture")
    return {
        "success": True,
        "execution_id": job["execution_id"],
        "arm": job["arm"],
        "seed": job["seed"],
        "result": str(result_path),
        "checkpoint_files": [
            str(root / filename) for filename in job["checkpoint_filenames"]
        ],
        "checkpoint_file_count": 3,
        "separate_final_model_artifact_written": False,
    }


def _materialize_training_prerequisites(
    protocol: dict, worker: dict, root: Path
) -> None:
    root.mkdir(parents=True, exist_ok=True)
    for job in worker["policy_training_jobs"]:
        _training_result(protocol, worker, job, root)


def _evidence_summary(
    protocol: dict, worker: dict, job: dict, root: Path
) -> dict:
    names = [job["label_filename"], job["probe_filename"]]
    schemas = [LABEL_EVIDENCE_SCHEMA_V1, PROBE_EVIDENCE_SCHEMA_V1]
    if job["split"] == "TRAIN":
        names.extend(
            [
                job["trajectory_metadata_filename"],
                job["trajectory_array_filename"],
            ]
        )
        schemas.extend([TRAJECTORY_EVIDENCE_SCHEMA_V1, None])
    paths = []
    for name, schema in zip(names, schemas, strict=True):
        path = root / name
        if schema is None:
            path.write_bytes(b"fixture-npz")
        else:
            _write_json(
                path,
                {
                    "schema": schema,
                    "protocol_id": protocol["protocol_id"],
                    "source_commit": protocol["source_commit"],
                    "player_identity": {
                        "player_key": job["player_key"],
                        "split": job["split"],
                    },
                    "execution_context": {
                        "execution_id": job["execution_id"],
                        "hostname": worker["expected_hostname"],
                        "device": worker["device"],
                    },
                },
            )
        paths.append(path)
    return {
        "success": True,
        "execution_id": job["execution_id"],
        "player_key": job["player_key"],
        "split": job["split"],
        "artifact_count": len(paths),
        "artifact_paths": {
            f"artifact_{index}": str(path) for index, path in enumerate(paths)
        },
    }


def _events(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def _completed_training_status_rows(worker: dict) -> list[dict]:
    jobs = worker["policy_training_jobs"]
    rows = [
        {"event": "WORKER_STARTED", "phase": "training", "worker": worker["worker"]}
    ]
    for ordinal, job in enumerate(jobs):
        rows.extend(
            [
                {
                    "event": "JOB_STARTED",
                    "phase": "training",
                    "worker": worker["worker"],
                    "job_ordinal": ordinal,
                    "execution_id": job["execution_id"],
                    "preexecution_identity_check_only": False,
                },
                {
                    "event": "JOB_COMPLETED",
                    "phase": "training",
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
            "phase": "training",
            "worker": worker["worker"],
            "completed_job_count": len(jobs),
        }
    )
    return rows


def test_training_worker_runs_exact_twenty_four_jobs_in_manifest_order(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    subject, protocol, manifest, worker, args = _fixture(
        tmp_path, phase="training"
    )
    _bind_runtime(subject, manifest, worker, monkeypatch)
    calls = []

    def runner(namespace):
        job = worker["policy_training_jobs"][len(calls)]
        calls.append(namespace.execution_id)
        assert namespace.execution_id == job["execution_id"]
        return _training_result(protocol, worker, job, args.results_root)

    summary = subject._run(args, training_job_runner=runner)
    events = _events(args.status_stream)

    assert summary["completed_job_count"] == len(calls) == 24
    assert calls == [job["execution_id"] for job in worker["policy_training_jobs"]]
    assert events[0]["event"] == "WORKER_STARTED"
    assert events[-1]["event"] == "WORKER_COMPLETED"
    assert sum(event["event"] == "JOB_STARTED" for event in events) == 24
    assert sum(event["event"] == "JOB_COMPLETED" for event in events) == 24
    assert not any(event["event"] == "JOB_FAILED" for event in events)


def test_evidence_worker_requires_training_then_runs_exact_seventy_two_players(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    subject, protocol, manifest, worker, args = _fixture(
        tmp_path, phase="evidence"
    )
    _bind_runtime(subject, manifest, worker, monkeypatch)
    _materialize_training_prerequisites(
        protocol, worker, args.results_root
    )
    calls = []

    def runner(namespace):
        job = worker["player_evidence_jobs"][len(calls)]
        calls.append(namespace.execution_id)
        assert namespace.snapshot == args.results_root / job["model_filename"]
        return _evidence_summary(protocol, worker, job, args.results_root)

    summary = subject._run(args, evidence_job_runner=runner)
    events = _events(args.status_stream)

    assert summary["completed_job_count"] == len(calls) == 72
    assert calls == [job["execution_id"] for job in worker["player_evidence_jobs"]]
    assert sum(event["event"] == "JOB_COMPLETED" for event in events) == 72
    assert events[-1]["event"] == "WORKER_COMPLETED"


def test_first_job_failure_stops_worker_without_retrying_or_running_later_jobs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    subject, _protocol, manifest, worker, args = _fixture(
        tmp_path, phase="training"
    )
    _bind_runtime(subject, manifest, worker, monkeypatch)
    calls = []

    def runner(namespace):
        calls.append(namespace.execution_id)
        raise RuntimeError("synthetic first-job failure")

    with pytest.raises(RuntimeError, match="synthetic first-job failure"):
        subject._run(args, training_job_runner=runner)
    events = _events(args.status_stream)

    assert calls == [worker["policy_training_jobs"][0]["execution_id"]]
    assert [event["event"] for event in events] == [
        "WORKER_STARTED",
        "JOB_STARTED",
        "JOB_FAILED",
        "WORKER_FAILED",
    ]


def test_any_preexisting_target_consumes_identity_before_any_job_runs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    subject, _protocol, manifest, worker, args = _fixture(
        tmp_path, phase="training"
    )
    _bind_runtime(subject, manifest, worker, monkeypatch)
    collision_job = worker["policy_training_jobs"][7]
    collision = args.results_root / collision_job["checkpoint_filenames"][1]
    collision.parent.mkdir(parents=True, exist_ok=True)
    collision.write_bytes(b"consumed")
    calls = []

    with pytest.raises(
        subject.LearnedResourceForecastWorkerV1Error,
        match="identity is consumed",
    ):
        subject._run(
            args,
            training_job_runner=lambda namespace: calls.append(namespace),
        )
    events = _events(args.status_stream)

    assert calls == []
    assert [event["event"] for event in events] == [
        "WORKER_STARTED",
        "JOB_STARTED",
        "JOB_FAILED",
        "WORKER_FAILED",
    ]
    assert events[2]["execution_id"] == collision_job["execution_id"]
    assert events[2]["failure_kind"] == "TARGET_ALREADY_EXISTS_IDENTITY_CONSUMED"


def test_existing_status_stream_forbids_a_second_worker_attempt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    subject, _protocol, manifest, worker, args = _fixture(
        tmp_path, phase="training"
    )
    _bind_runtime(subject, manifest, worker, monkeypatch)
    args.status_stream.parent.mkdir(parents=True, exist_ok=True)
    args.status_stream.write_text("retained prior attempt\n", encoding="utf-8")

    with pytest.raises(
        subject.LearnedResourceForecastWorkerV1Error,
        match="phase identity is consumed",
    ):
        subject._run(args, training_job_runner=lambda _namespace: {})
    assert args.status_stream.read_text(encoding="utf-8") == "retained prior attempt\n"


def test_evidence_phase_fails_before_jobs_when_training_matrix_is_incomplete(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    subject, _protocol, manifest, worker, args = _fixture(
        tmp_path, phase="evidence"
    )
    _bind_runtime(subject, manifest, worker, monkeypatch)
    calls = []

    with pytest.raises(
        subject.LearnedResourceForecastWorkerV1Error,
        match="not the exact 24-JSON 72-PT roster",
    ):
        subject._run(
            args,
            evidence_job_runner=lambda namespace: calls.append(namespace),
        )
    events = _events(args.status_stream)

    assert calls == []
    assert [event["event"] for event in events] == [
        "WORKER_STARTED",
        "WORKER_FAILED",
    ]


def test_evidence_phase_rejects_foreign_file_in_otherwise_complete_worker_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    subject, protocol, manifest, worker, args = _fixture(
        tmp_path, phase="evidence"
    )
    _bind_runtime(subject, manifest, worker, monkeypatch)
    _materialize_training_prerequisites(protocol, worker, args.results_root)
    (args.results_root / "foreign.txt").write_text("foreign", encoding="utf-8")

    with pytest.raises(
        subject.LearnedResourceForecastWorkerV1Error,
        match="not the exact 24-JSON 72-PT roster",
    ):
        subject._run(args, evidence_job_runner=lambda _namespace: {})
    assert [event["event"] for event in _events(args.status_stream)] == [
        "WORKER_STARTED",
        "WORKER_FAILED",
    ]


@pytest.mark.parametrize(
    ("field", "foreign_value"),
    [
        ("pythonpath_environment", "/foreign/src"),
        ("acfqp_file", "/foreign/src/acfqp/__init__.py"),
    ],
)
def test_runtime_binding_rejects_foreign_pythonpath_or_acfqp_import(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    field: str,
    foreign_value: str,
) -> None:
    subject, _protocol, manifest, worker, args = _fixture(
        tmp_path, phase="training"
    )
    _bind_runtime(subject, manifest, worker, monkeypatch)
    context = subject._actual_runtime_context(args.device)
    context[field] = foreign_value

    with pytest.raises(
        subject.LearnedResourceForecastWorkerV1Error,
        match="differs from the launch manifest",
    ):
        subject._validate_runtime_binding(
            worker=worker,
            required_runtime=manifest["required_runtime"],
            source_checkout=manifest["source_checkout"],
            source_pythonpath=manifest["source_pythonpath"],
            requested_device=args.device,
            context=context,
        )


def test_training_global_preflight_is_read_only_before_fixed_roots_exist(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    subject, _protocol, manifest, worker, args = _fixture(
        tmp_path, phase="training"
    )
    _bind_runtime(subject, manifest, worker, monkeypatch)
    args.results_root.rmdir()
    args.results_root.parent.rmdir()
    args.global_preflight_only = True

    summary = subject._run(args)

    assert summary["success"] is True
    assert summary["global_preflight_only"] is True
    assert summary["filesystem_mutation"] is False
    assert not Path(manifest["fixed_paths"]["results_root"]).exists()
    assert not Path(manifest["fixed_paths"]["status_root"]).exists()
    assert not Path(manifest["fixed_paths"]["log_root"]).exists()
    assert not args.status_stream.exists()


def test_evidence_global_preflight_requires_exact_training_roster_without_writes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    subject, protocol, manifest, worker, args = _fixture(
        tmp_path, phase="evidence"
    )
    _bind_runtime(subject, manifest, worker, monkeypatch)
    host_workers = [
        candidate
        for candidate in manifest["workers"]
        if candidate["host_alias"] == worker["host_alias"]
    ]
    status_root = Path(manifest["fixed_paths"]["status_root"])
    log_root = Path(manifest["fixed_paths"]["log_root"])
    status_root.mkdir(parents=True, exist_ok=True)
    log_root.mkdir(parents=True, exist_ok=True)
    for candidate in host_workers:
        candidate_root = (
            Path(manifest["fixed_paths"]["results_root"])
            / f"worker-{candidate['worker']}"
        )
        _materialize_training_prerequisites(protocol, candidate, candidate_root)
        _write_json(
            log_root / f"worker-{candidate['worker']}-training.log",
            {
                "success": True,
                "phase": "training",
                "worker": candidate["worker"],
                "completed_job_count": 24,
                "results_root": str(candidate_root),
            },
        )
        status_path = status_root / candidate["policy_training_status_stream"]
        status_path.write_bytes(
            b"".join(
                canonical_json_bytes(row) + b"\n"
                for row in _completed_training_status_rows(candidate)
            )
        )
    args.global_preflight_only = True

    summary = subject._run(args)

    assert summary["success"] is True
    assert summary["global_preflight_only"] is True
    assert summary["filesystem_mutation"] is False
    assert not args.status_stream.exists()
    assert {path.name for path in args.results_root.iterdir()} == (
        subject._training_artifact_names(worker)
    )


def test_evidence_global_preflight_rejects_unclosed_training_status_without_writes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    subject, protocol, manifest, worker, args = _fixture(
        tmp_path, phase="evidence"
    )
    _bind_runtime(subject, manifest, worker, monkeypatch)
    host_workers = [
        candidate
        for candidate in manifest["workers"]
        if candidate["host_alias"] == worker["host_alias"]
    ]
    status_root = Path(manifest["fixed_paths"]["status_root"])
    log_root = Path(manifest["fixed_paths"]["log_root"])
    status_root.mkdir(parents=True, exist_ok=True)
    log_root.mkdir(parents=True, exist_ok=True)
    for candidate in host_workers:
        candidate_root = (
            Path(manifest["fixed_paths"]["results_root"])
            / f"worker-{candidate['worker']}"
        )
        _materialize_training_prerequisites(protocol, candidate, candidate_root)
        rows = _completed_training_status_rows(candidate)
        if candidate["worker"] == worker["worker"]:
            rows = rows[:-1]
        (status_root / candidate["policy_training_status_stream"]).write_bytes(
            b"".join(canonical_json_bytes(row) + b"\n" for row in rows)
        )
        _write_json(
            log_root / f"worker-{candidate['worker']}-training.log",
            {
                "success": True,
                "phase": "training",
                "worker": candidate["worker"],
                "completed_job_count": 24,
                "results_root": str(candidate_root),
            },
        )
    args.global_preflight_only = True

    with pytest.raises(Exception, match="status lifecycle is not exactly complete"):
        subject._run(args)
    assert not args.status_stream.exists()
