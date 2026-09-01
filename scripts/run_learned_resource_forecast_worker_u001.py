#!/usr/bin/env python3
"""Run one fixed U001 GPU worker phase without retries or identity reuse."""

from __future__ import annotations

import argparse
import gc
import importlib.util
import json
import os
from pathlib import Path
import socket
import sys
from types import SimpleNamespace
from typing import Any, Callable

import acfqp
from acfqp.phase3e_ids import canonical_json_bytes
from acfqp.science.execution_io_v1 import (
    ScienceExecutionIOV1Error,
    bound_clean_source_commit_v1,
    require_path_outside_repository_v1,
)
from acfqp.science.learned_resource_forecast_evidence_v1 import (
    LABEL_EVIDENCE_SCHEMA_V1,
    PROBE_EVIDENCE_SCHEMA_V1,
    TRAJECTORY_EVIDENCE_SCHEMA_V1,
)
from acfqp.science.learned_resource_forecast_protocol_v1 import (
    LearnedResourceForecastProtocolV1Error,
    validate_ratified_learned_resource_forecast_protocol_v1,
)
from acfqp.science.matched_double_dqn_2048_learned_resource_pilot_v1 import (
    LEARNED_RESOURCE_POLICY_TRAINING_RESULT_SCHEMA_V1,
)


REPOSITORY = Path(__file__).resolve().parents[1]
PHASES_V1 = ("training", "evidence")
WORKER_COUNT_V1 = 6
TRAINING_JOBS_PER_WORKER_V1 = 24
EVIDENCE_JOBS_PER_WORKER_V1 = 72
JobRunnerV1 = Callable[[SimpleNamespace], dict[str, Any]]


class LearnedResourceForecastWorkerV1Error(RuntimeError):
    """A worker binding, prerequisite, identity, or artifact is ineligible."""


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--worker", type=int, choices=range(WORKER_COUNT_V1), required=True
    )
    parser.add_argument("--phase", choices=PHASES_V1, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--results-root", type=Path, required=True)
    parser.add_argument("--status-stream", type=Path, required=True)
    parser.add_argument("--device", required=True)
    parser.add_argument("--preflight-only", action="store_true")
    parser.add_argument("--global-preflight-only", action="store_true")
    return parser.parse_args()


def _read_object(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise LearnedResourceForecastWorkerV1Error(
            f"cannot read {label} as one JSON object: {path}"
        ) from error
    if type(value) is not dict:
        raise LearnedResourceForecastWorkerV1Error(
            f"{label} must contain one JSON object"
        )
    return value


def _load_script_module(name: str, filename: str):
    path = REPOSITORY / "scripts" / filename
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise LearnedResourceForecastWorkerV1Error(
            f"cannot load registered worker dependency: {path}"
        )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _expected_manifest(protocol: dict[str, Any]) -> dict[str, Any]:
    module = _load_script_module(
        "acfqp_u001_prepare_for_worker",
        "prepare_learned_resource_forecast_campaign_u001.py",
    )
    return module.build_launch_manifest_v1(protocol)


def _actual_runtime_context(device_name: str) -> dict[str, Any]:
    import numpy as np
    import scipy
    import torch

    if type(device_name) is not str or not device_name:
        raise LearnedResourceForecastWorkerV1Error(
            "worker device must be one exact nonempty string"
        )
    device = torch.device(device_name)
    if device.type != "cuda" or not torch.cuda.is_available():
        raise LearnedResourceForecastWorkerV1Error(
            "formal U001 workers require one available CUDA device"
        )
    try:
        device_name_observed = torch.cuda.get_device_name(device)
    except (AssertionError, RuntimeError, ValueError) as error:
        raise LearnedResourceForecastWorkerV1Error(
            "registered CUDA ordinal is unavailable"
        ) from error
    return {
        "hostname": socket.gethostname(),
        "python_version": ".".join(
            str(component) for component in sys.version_info[:3]
        ),
        "python_path": str(Path(sys.executable).resolve()),
        "pythonpath_environment": os.environ.get("PYTHONPATH"),
        "sys_path": list(sys.path),
        "acfqp_file": str(Path(acfqp.__file__).resolve()),
        "numpy_version": np.__version__,
        "scipy_version": scipy.__version__,
        "torch_version": str(torch.__version__),
        "torch_cuda_runtime_version": torch.version.cuda,
        "torch_cudnn_version": torch.backends.cudnn.version(),
        "device": str(device),
        "cuda_device_name": device_name_observed,
    }


def _validate_runtime_binding(
    *,
    worker: dict[str, Any],
    required_runtime: dict[str, Any],
    source_checkout: str,
    source_pythonpath: str,
    requested_device: str,
    context: dict[str, Any],
) -> None:
    expected_source = Path(source_checkout).resolve()
    expected_pythonpath = Path(source_pythonpath).resolve()
    resolved_sys_path = []
    for entry in context.get("sys_path", []):
        if type(entry) is not str:
            raise LearnedResourceForecastWorkerV1Error(
                "worker sys.path contains a non-string entry"
            )
        resolved_sys_path.append(Path(entry or ".").resolve())
    acfqp_file = Path(str(context.get("acfqp_file", ""))).resolve()
    required_pairs = {
        "python_version": required_runtime["python_version"],
        "numpy_version": required_runtime["numpy_version"],
        "scipy_version": required_runtime["scipy_version"],
        "torch_version": required_runtime["torch_version"],
        "torch_cuda_runtime_version": required_runtime[
            "torch_cuda_runtime_version"
        ],
    }
    if (
        requested_device != worker["device"]
        or context.get("device") != worker["device"]
        or context.get("hostname") != worker["expected_hostname"]
        or any(context.get(name) != value for name, value in required_pairs.items())
        or Path(str(context.get("python_path", ""))).resolve()
        != Path(worker["python"]).resolve()
        or Path(worker["python"]).resolve()
        != Path(required_runtime["python_path"]).resolve()
        or expected_source != REPOSITORY.resolve()
        or expected_pythonpath != expected_source / "src"
        or Path(required_runtime["source_pythonpath"]).resolve()
        != expected_pythonpath
        or context.get("pythonpath_environment") != str(expected_pythonpath)
        or resolved_sys_path.count(expected_pythonpath) != 1
        or expected_pythonpath not in acfqp_file.parents
        or required_runtime.get(
            "acfqp_import_must_resolve_inside_source_pythonpath"
        )
        is not True
        or required_runtime.get(
            "pythonpath_environment_must_equal_source_pythonpath"
        )
        is not True
    ):
        raise LearnedResourceForecastWorkerV1Error(
            "actual worker host, device, Python, or dependency tuple differs "
            "from the launch manifest"
        )


class _ExclusiveStatusStreamV1:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._fd: int | None = None

    def __enter__(self) -> "_ExclusiveStatusStreamV1":
        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self._fd = os.open(
                self.path,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC,
                0o600,
            )
        except FileExistsError as error:
            raise LearnedResourceForecastWorkerV1Error(
                "worker status stream already exists; the phase identity is consumed"
            ) from error
        return self

    def emit(self, document: dict[str, Any]) -> None:
        if self._fd is None or type(document) is not dict:
            raise LearnedResourceForecastWorkerV1Error(
                "worker status stream is not open for one JSON event"
            )
        raw = canonical_json_bytes(document) + b"\n"
        view = memoryview(raw)
        while view:
            written = os.write(self._fd, view)
            view = view[written:]
        os.fsync(self._fd)

    def __exit__(self, _type, _value, _traceback) -> None:
        if self._fd is not None:
            os.close(self._fd)
            self._fd = None


def _training_targets(job: dict[str, Any], results_root: Path) -> tuple[Path, ...]:
    return (
        results_root / job["result_filename"],
        *(results_root / name for name in job["checkpoint_filenames"]),
    )


def _evidence_targets(job: dict[str, Any], results_root: Path) -> tuple[Path, ...]:
    names = [job["label_filename"], job["probe_filename"]]
    if job["split"] == "TRAIN":
        names.extend(
            [
                job["trajectory_metadata_filename"],
                job["trajectory_array_filename"],
            ]
        )
    if any(type(name) is not str or not name for name in names):
        raise LearnedResourceForecastWorkerV1Error(
            "player-evidence target roster changed"
        )
    return tuple(results_root / name for name in names)


def _validate_training_result(
    *, protocol: dict[str, Any], worker: dict[str, Any], job: dict[str, Any], root: Path
) -> None:
    targets = _training_targets(job, root)
    if not all(path.is_file() for path in targets):
        raise LearnedResourceForecastWorkerV1Error(
            "completed policy-training job did not materialize one JSON and "
            "three snapshots"
        )
    result = _read_object(targets[0], "policy-training result")
    checkpoint_rows = result.get("artifact_manifest", {}).get("checkpoint_files")
    if (
        result.get("schema") != LEARNED_RESOURCE_POLICY_TRAINING_RESULT_SCHEMA_V1
        or result.get("protocol_id") != protocol["protocol_id"]
        or result.get("arm") != job["arm"]
        or result.get("seed") != job["seed"]
        or result.get("device") != worker["device"]
        or result.get("execution_context", {}).get("execution_id")
        != job["execution_id"]
        or result.get("execution_context", {}).get("source_commit")
        != protocol["source_commit"]
        or result.get("execution_context", {}).get("hostname")
        != worker["expected_hostname"]
        or result.get("execution_context", {}).get("device") != worker["device"]
        or type(checkpoint_rows) is not list
        or [
            row.get("checkpoint_environment_interactions")
            for row in checkpoint_rows
        ]
        != protocol["training"]["evaluation_checkpoints"]
        or [row.get("filename") for row in checkpoint_rows]
        != job["checkpoint_filenames"]
        or any(
            row.get("artifact_kind")
            != "INFERENCE_ONLY_BARE_ONLINE_STATE_DICT"
            for row in checkpoint_rows
        )
        or result.get("artifact_manifest", {}).get("result_filename")
        != job["result_filename"]
        or result.get("artifact_manifest", {}).get("checkpoint_file_count") != 3
        or result.get("artifact_manifest", {}).get(
            "separate_final_model_artifact_written"
        )
        is not False
    ):
        raise LearnedResourceForecastWorkerV1Error(
            "policy-training result does not replay its manifest identity"
        )


def _validate_all_training_prerequisites(
    *, protocol: dict[str, Any], worker: dict[str, Any], root: Path
) -> None:
    jobs = worker["policy_training_jobs"]
    if len(jobs) != TRAINING_JOBS_PER_WORKER_V1:
        raise LearnedResourceForecastWorkerV1Error(
            "evidence worker no longer has exactly 24 training prerequisites"
        )
    for job in jobs:
        _validate_training_result(
            protocol=protocol, worker=worker, job=job, root=root
        )


def _training_artifact_names(worker: dict[str, Any]) -> set[str]:
    names: set[str] = set()
    for job in worker["policy_training_jobs"]:
        names.add(job["result_filename"])
        names.update(job["checkpoint_filenames"])
    if len(names) != TRAINING_JOBS_PER_WORKER_V1 * 4:
        raise LearnedResourceForecastWorkerV1Error(
            "worker training artifact allowlist changed"
        )
    return names


def _validate_worker_directory_for_phase(
    *, phase: str, worker: dict[str, Any], root: Path
) -> None:
    if not root.is_dir():
        raise LearnedResourceForecastWorkerV1Error(
            "launcher did not provide one worker result directory"
        )
    entries = list(root.iterdir())
    if phase == "training":
        if entries:
            raise LearnedResourceForecastWorkerV1Error(
                "training worker result directory is not exactly empty; "
                "the worker identity is consumed"
            )
        return
    expected_names = _training_artifact_names(worker)
    if (
        any(not path.is_file() for path in entries)
        or {path.name for path in entries} != expected_names
    ):
        raise LearnedResourceForecastWorkerV1Error(
            "evidence worker directory is not the exact 24-JSON 72-PT roster"
        )


def _validate_training_summary(
    summary: dict[str, Any], job: dict[str, Any], targets: tuple[Path, ...]
) -> None:
    if (
        type(summary) is not dict
        or summary.get("success") is not True
        or summary.get("execution_id") != job["execution_id"]
        or summary.get("arm") != job["arm"]
        or summary.get("seed") != job["seed"]
        or Path(str(summary.get("result", ""))).resolve() != targets[0].resolve()
        or [Path(path).resolve() for path in summary.get("checkpoint_files", [])]
        != [path.resolve() for path in targets[1:]]
        or summary.get("checkpoint_file_count") != 3
        or summary.get("separate_final_model_artifact_written") is not False
    ):
        raise LearnedResourceForecastWorkerV1Error(
            "policy-training job runner returned a foreign summary"
        )


def _validate_evidence_summary(
    summary: dict[str, Any], job: dict[str, Any], targets: tuple[Path, ...]
) -> None:
    if (
        type(summary) is not dict
        or summary.get("success") is not True
        or summary.get("execution_id") != job["execution_id"]
        or summary.get("player_key") != job["player_key"]
        or summary.get("split") != job["split"]
        or summary.get("artifact_count") != len(targets)
        or {Path(path).resolve() for path in summary.get("artifact_paths", {}).values()}
        != {path.resolve() for path in targets}
        or not all(path.is_file() for path in targets)
    ):
        raise LearnedResourceForecastWorkerV1Error(
            "player-evidence job runner returned a foreign or incomplete summary"
        )


def _validate_evidence_artifacts(
    *,
    protocol: dict[str, Any],
    worker: dict[str, Any],
    job: dict[str, Any],
    root: Path,
) -> None:
    json_contracts = [
        (job["label_filename"], LABEL_EVIDENCE_SCHEMA_V1),
        (job["probe_filename"], PROBE_EVIDENCE_SCHEMA_V1),
    ]
    if job["split"] == "TRAIN":
        json_contracts.append(
            (job["trajectory_metadata_filename"], TRAJECTORY_EVIDENCE_SCHEMA_V1)
        )
        trajectory_array = root / job["trajectory_array_filename"]
        if not trajectory_array.is_file():
            raise LearnedResourceForecastWorkerV1Error(
                "completed train-player evidence lost its trajectory array"
            )
    for filename, schema in json_contracts:
        document = _read_object(root / filename, "player-evidence lane artifact")
        if (
            document.get("schema") != schema
            or document.get("protocol_id") != protocol["protocol_id"]
            or document.get("source_commit") != protocol["source_commit"]
            or document.get("player_identity", {}).get("player_key")
            != job["player_key"]
            or document.get("player_identity", {}).get("split") != job["split"]
            or document.get("execution_context", {}).get("execution_id")
            != job["execution_id"]
            or document.get("execution_context", {}).get("hostname")
            != worker["expected_hostname"]
            or document.get("execution_context", {}).get("device")
            != worker["device"]
        ):
            raise LearnedResourceForecastWorkerV1Error(
                "player-evidence lane artifact does not replay its manifest identity"
            )


def _run_policy_training_job(args: SimpleNamespace) -> dict[str, Any]:
    module = _load_script_module(
        "acfqp_u001_policy_training_for_worker",
        "run_learned_resource_policy_training_u001.py",
    )
    return module._run(args)


def _run_player_evidence_job(args: SimpleNamespace) -> dict[str, Any]:
    module = _load_script_module(
        "acfqp_u001_player_evidence_for_worker",
        "run_learned_resource_player_evidence_u001.py",
    )
    return module._run(args)


def _release_job_memory() -> None:
    gc.collect()
    try:
        import torch
    except ImportError:  # pragma: no cover - formal runtime always has Torch
        return
    if torch.cuda.is_available():
        torch.cuda.empty_cache()


def _job_identity_fields(job: dict[str, Any]) -> dict[str, Any]:
    fields = {
        "execution_id": job["execution_id"],
        "arm": job["arm"],
        "seed": job["seed"],
    }
    if "checkpoint" in job:
        fields["checkpoint"] = job["checkpoint"]
        fields["player_key"] = job["player_key"]
    return fields


def _fail_on_preexisting_target(
    *,
    phase: str,
    worker_index: int,
    jobs: list[dict[str, Any]],
    root: Path,
    status: _ExclusiveStatusStreamV1,
) -> None:
    target_builder = _training_targets if phase == "training" else _evidence_targets
    for ordinal, job in enumerate(jobs):
        existing = [
            str(path)
            for path in target_builder(job, root)
            if path.exists()
        ]
        if existing:
            status.emit(
                {
                    "event": "JOB_STARTED",
                    "phase": phase,
                    "worker": worker_index,
                    "job_ordinal": ordinal,
                    "preexecution_identity_check_only": True,
                    **_job_identity_fields(job),
                }
            )
            status.emit(
                {
                    "event": "JOB_FAILED",
                    "phase": phase,
                    "worker": worker_index,
                    "job_ordinal": ordinal,
                    "failure_kind": "TARGET_ALREADY_EXISTS_IDENTITY_CONSUMED",
                    "existing_targets": existing,
                    **_job_identity_fields(job),
                }
            )
            raise LearnedResourceForecastWorkerV1Error(
                "worker target already exists; the job identity is consumed"
            )


def _require_no_preexisting_phase_targets(
    *, phase: str, jobs: list[dict[str, Any]], root: Path
) -> None:
    target_builder = _training_targets if phase == "training" else _evidence_targets
    if any(path.exists() for job in jobs for path in target_builder(job, root)):
        raise LearnedResourceForecastWorkerV1Error(
            "worker target already exists; the job identity is consumed"
        )


def _validate_host_training_closure_for_evidence(
    *, protocol: dict[str, Any], manifest: dict[str, Any], worker: dict[str, Any]
) -> None:
    postprocess = _load_script_module(
        "acfqp_u001_postprocess_for_worker_preflight",
        "postprocess_retain_learned_resource_forecast_u001.py",
    )
    fixed = manifest["fixed_paths"]
    host_workers = [
        candidate
        for candidate in manifest["workers"]
        if candidate["host_alias"] == worker["host_alias"]
    ]
    if len(host_workers) != 2:
        raise LearnedResourceForecastWorkerV1Error(
            "evidence preflight host no longer owns exactly two workers"
        )
    results_root = Path(fixed["results_root"])
    status_root = Path(fixed["status_root"])
    log_root = Path(fixed["log_root"])
    expected_worker_names = {
        f"worker-{candidate['worker']}" for candidate in host_workers
    }
    if (
        not results_root.is_dir()
        or {path.name for path in results_root.iterdir()} != expected_worker_names
        or any(not path.is_dir() for path in results_root.iterdir())
    ):
        raise LearnedResourceForecastWorkerV1Error(
            "evidence preflight host results root is missing or foreign"
        )
    expected_status_names = {
        candidate["policy_training_status_stream"] for candidate in host_workers
    }
    expected_log_names = {
        f"worker-{candidate['worker']}-training.log" for candidate in host_workers
    }
    postprocess._require_exact_directory(
        status_root, expected_status_names, "host training status root"
    )
    postprocess._require_exact_directory(
        log_root, expected_log_names, "host training log root"
    )
    for candidate in host_workers:
        candidate_root = results_root / f"worker-{candidate['worker']}"
        postprocess._require_exact_directory(
            candidate_root,
            _training_artifact_names(candidate),
            f"host worker-{candidate['worker']} training directory",
        )
        _validate_all_training_prerequisites(
            protocol=protocol, worker=candidate, root=candidate_root
        )
        postprocess._validate_worker_status(
            status_root / candidate["policy_training_status_stream"],
            phase="training",
            worker=candidate,
        )
        postprocess._validate_worker_log(
            log_root / f"worker-{candidate['worker']}-training.log",
            phase="training",
            worker=candidate,
            results_root=candidate_root,
        )


def _execute_jobs(
    *,
    phase: str,
    protocol: dict[str, Any],
    worker: dict[str, Any],
    worker_index: int,
    protocol_path: Path,
    root: Path,
    device: str,
    status: _ExclusiveStatusStreamV1,
    runner: JobRunnerV1,
) -> int:
    jobs = (
        worker["policy_training_jobs"]
        if phase == "training"
        else worker["player_evidence_jobs"]
    )
    expected_count = (
        TRAINING_JOBS_PER_WORKER_V1
        if phase == "training"
        else EVIDENCE_JOBS_PER_WORKER_V1
    )
    if len(jobs) != expected_count:
        raise LearnedResourceForecastWorkerV1Error(
            "worker phase job count differs from the frozen roster"
        )
    _fail_on_preexisting_target(
        phase=phase,
        worker_index=worker_index,
        jobs=jobs,
        root=root,
        status=status,
    )
    completed = 0
    for ordinal, job in enumerate(jobs):
        status.emit(
            {
                "event": "JOB_STARTED",
                "phase": phase,
                "worker": worker_index,
                "job_ordinal": ordinal,
                "preexecution_identity_check_only": False,
                **_job_identity_fields(job),
            }
        )
        if phase == "training":
            targets = _training_targets(job, root)
            arguments = SimpleNamespace(
                protocol=protocol_path,
                arm=job["arm"],
                seed=job["seed"],
                device=device,
                output_dir=root,
                execution_id=job["execution_id"],
            )
        else:
            targets = _evidence_targets(job, root)
            arguments = SimpleNamespace(
                protocol=protocol_path,
                snapshot=root / job["model_filename"],
                arm=job["arm"],
                seed=job["seed"],
                checkpoint=job["checkpoint"],
                device=device,
                output_dir=root,
                execution_id=job["execution_id"],
            )
        try:
            summary = runner(arguments)
            if phase == "training":
                _validate_training_summary(summary, job, targets)
                _validate_training_result(
                    protocol=protocol, worker=worker, job=job, root=root
                )
            else:
                _validate_evidence_summary(summary, job, targets)
                _validate_evidence_artifacts(
                    protocol=protocol, worker=worker, job=job, root=root
                )
        except Exception as error:
            status.emit(
                {
                    "event": "JOB_FAILED",
                    "phase": phase,
                    "worker": worker_index,
                    "job_ordinal": ordinal,
                    "failure_kind": type(error).__name__,
                    "failure_message": str(error),
                    **_job_identity_fields(job),
                }
            )
            raise
        finally:
            _release_job_memory()
        completed += 1
        status.emit(
            {
                "event": "JOB_COMPLETED",
                "phase": phase,
                "worker": worker_index,
                "job_ordinal": ordinal,
                "completed_job_count": completed,
                "expected_job_count": expected_count,
                **_job_identity_fields(job),
            }
        )
    return completed


def _run(
    args: argparse.Namespace,
    *,
    training_job_runner: JobRunnerV1 | None = None,
    evidence_job_runner: JobRunnerV1 | None = None,
) -> dict[str, Any]:
    if args.worker not in range(WORKER_COUNT_V1) or args.phase not in PHASES_V1:
        raise LearnedResourceForecastWorkerV1Error(
            "worker index or phase is outside the frozen U001 roster"
        )
    protocol_path = require_path_outside_repository_v1(
        repository=REPOSITORY,
        path=args.protocol,
        label="ratified U001 protocol input",
    )
    manifest_path = require_path_outside_repository_v1(
        repository=REPOSITORY,
        path=args.manifest,
        label="U001 launch manifest input",
    )
    root = require_path_outside_repository_v1(
        repository=REPOSITORY,
        path=args.results_root,
        label="U001 worker results root",
    )
    status_path = require_path_outside_repository_v1(
        repository=REPOSITORY,
        path=args.status_stream,
        label="U001 worker status stream",
    )
    source_commit = bound_clean_source_commit_v1(REPOSITORY)
    protocol = validate_ratified_learned_resource_forecast_protocol_v1(
        _read_object(protocol_path, "ratified U001 protocol")
    )
    manifest = _read_object(manifest_path, "U001 launch manifest")
    if manifest != _expected_manifest(protocol):
        raise LearnedResourceForecastWorkerV1Error(
            "launch manifest does not replay from the ratified protocol"
        )
    if (
        protocol["source_commit"] != source_commit
        or manifest["source_commit"] != source_commit
        or manifest["protocol_id"] != protocol["protocol_id"]
        or manifest["worker_count"] != WORKER_COUNT_V1
        or Path(manifest["source_checkout"]).resolve() != REPOSITORY.resolve()
        or Path(manifest["source_pythonpath"]).resolve()
        != REPOSITORY.resolve() / "src"
    ):
        raise LearnedResourceForecastWorkerV1Error(
            "clean source, protocol, and launch manifest binding changed"
        )
    worker = manifest["workers"][args.worker]
    if worker.get("worker") != args.worker:
        raise LearnedResourceForecastWorkerV1Error(
            "worker manifest ordinal changed"
        )
    expected_status_name = worker[
        "policy_training_status_stream"
        if args.phase == "training"
        else "player_evidence_status_stream"
    ]
    if status_path.name != expected_status_name:
        raise LearnedResourceForecastWorkerV1Error(
            "status-stream basename differs from the worker manifest"
        )
    fixed = manifest["fixed_paths"]
    expected_root = Path(fixed["results_root"]) / f"worker-{args.worker}"
    expected_status = Path(fixed["status_root"]) / expected_status_name
    if (
        protocol_path != Path(fixed["protocol"]).resolve()
        or manifest_path != Path(fixed["manifest"]).resolve()
        or root != expected_root.resolve()
        or status_path != expected_status.resolve()
    ):
        raise LearnedResourceForecastWorkerV1Error(
            "worker inputs or outputs differ from the fixed manifest paths"
        )

    runner = (
        training_job_runner or _run_policy_training_job
        if args.phase == "training"
        else evidence_job_runner or _run_player_evidence_job
    )
    if getattr(args, "global_preflight_only", False):
        if getattr(args, "preflight_only", False):
            raise LearnedResourceForecastWorkerV1Error(
                "worker preflight modes are mutually exclusive"
            )
        context = _actual_runtime_context(args.device)
        _validate_runtime_binding(
            worker=worker,
            required_runtime=manifest["required_runtime"],
            source_checkout=manifest["source_checkout"],
            source_pythonpath=manifest["source_pythonpath"],
            requested_device=args.device,
            context=context,
        )
        if args.phase == "training":
            if any(
                Path(fixed[key]).exists()
                for key in ("results_root", "status_root", "log_root")
            ):
                raise LearnedResourceForecastWorkerV1Error(
                    "training global preflight requires absent fixed roots"
                )
        else:
            if status_path.exists():
                raise LearnedResourceForecastWorkerV1Error(
                    "evidence worker status target is already consumed"
                )
            phase_jobs = worker["player_evidence_jobs"]
            _require_no_preexisting_phase_targets(
                phase=args.phase, jobs=phase_jobs, root=root
            )
            _validate_host_training_closure_for_evidence(
                protocol=protocol, manifest=manifest, worker=worker
            )
        return {
            "success": True,
            "global_preflight_only": True,
            "phase": args.phase,
            "worker": args.worker,
            "source_commit": source_commit,
            "protocol_id": protocol["protocol_id"],
            "runtime_context": context,
            "filesystem_mutation": False,
        }
    if getattr(args, "preflight_only", False):
        if status_path.exists():
            raise LearnedResourceForecastWorkerV1Error(
                "worker status already exists; the phase identity is consumed"
            )
        context = _actual_runtime_context(args.device)
        _validate_runtime_binding(
            worker=worker,
            required_runtime=manifest["required_runtime"],
            source_checkout=manifest["source_checkout"],
            source_pythonpath=manifest["source_pythonpath"],
            requested_device=args.device,
            context=context,
        )
        phase_jobs = (
            worker["policy_training_jobs"]
            if args.phase == "training"
            else worker["player_evidence_jobs"]
        )
        _require_no_preexisting_phase_targets(
            phase=args.phase, jobs=phase_jobs, root=root
        )
        _validate_worker_directory_for_phase(
            phase=args.phase, worker=worker, root=root
        )
        if args.phase == "evidence":
            _validate_all_training_prerequisites(
                protocol=protocol, worker=worker, root=root
            )
        return {
            "success": True,
            "preflight_only": True,
            "phase": args.phase,
            "worker": args.worker,
            "source_commit": source_commit,
            "protocol_id": protocol["protocol_id"],
            "results_root": str(root),
            "status_stream": str(status_path),
            "runtime_context": context,
        }
    with _ExclusiveStatusStreamV1(status_path) as status:
        status.emit(
            {
                "event": "WORKER_STARTED",
                "phase": args.phase,
                "worker": args.worker,
                "host_alias": worker["host_alias"],
                "expected_hostname": worker["expected_hostname"],
                "device": args.device,
                "source_commit": source_commit,
                "protocol_id": protocol["protocol_id"],
            }
        )
        try:
            context = _actual_runtime_context(args.device)
            _validate_runtime_binding(
                worker=worker,
                required_runtime=manifest["required_runtime"],
                source_checkout=manifest["source_checkout"],
                source_pythonpath=manifest["source_pythonpath"],
                requested_device=args.device,
                context=context,
            )
            phase_jobs = (
                worker["policy_training_jobs"]
                if args.phase == "training"
                else worker["player_evidence_jobs"]
            )
            _fail_on_preexisting_target(
                phase=args.phase,
                worker_index=args.worker,
                jobs=phase_jobs,
                root=root,
                status=status,
            )
            _validate_worker_directory_for_phase(
                phase=args.phase, worker=worker, root=root
            )
            if args.phase == "evidence":
                _validate_all_training_prerequisites(
                    protocol=protocol, worker=worker, root=root
                )
            completed = _execute_jobs(
                phase=args.phase,
                protocol=protocol,
                worker=worker,
                worker_index=args.worker,
                protocol_path=protocol_path,
                root=root,
                device=args.device,
                status=status,
                runner=runner,
            )
        except Exception as error:
            status.emit(
                {
                    "event": "WORKER_FAILED",
                    "phase": args.phase,
                    "worker": args.worker,
                    "failure_kind": type(error).__name__,
                    "failure_message": str(error),
                }
            )
            raise
        status.emit(
            {
                "event": "WORKER_COMPLETED",
                "phase": args.phase,
                "worker": args.worker,
                "completed_job_count": completed,
                "runtime_context": context,
            }
        )
    return {
        "success": True,
        "phase": args.phase,
        "worker": args.worker,
        "completed_job_count": completed,
        "source_commit": source_commit,
        "protocol_id": protocol["protocol_id"],
        "status_stream": str(status_path),
        "results_root": str(root),
    }


def main() -> int:
    try:
        summary = _run(_arguments())
    except (
        LearnedResourceForecastProtocolV1Error,
        LearnedResourceForecastWorkerV1Error,
        ScienceExecutionIOV1Error,
    ) as error:
        raise SystemExit(str(error)) from error
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
