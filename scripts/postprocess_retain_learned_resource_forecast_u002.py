#!/usr/bin/env python3
"""Run the one-shot U002 analysis, verification, and server-side retention."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
from pathlib import Path
import shutil
import socket
import sys
from types import SimpleNamespace
from typing import Any, Callable

from acfqp.phase3e_ids import canonical_json_bytes
from acfqp.science.execution_io_v1 import (
    ScienceExecutionIOV1Error,
    bound_clean_source_commit_v1,
    require_path_outside_repository_v1,
    write_exclusive_bytes_v1,
)
from acfqp.science.learned_resource_forecast_protocol_v1 import (
    LearnedResourceForecastProtocolV1Error,
    validate_ratified_learned_resource_forecast_protocol_v1,
)


REPOSITORY = Path(__file__).resolve().parents[1]
SCHEMA_V1 = "acfqp.science.learned_resource_forecast_postprocess_retention.v1"
INVENTORY_FILENAME_V1 = "retention-inventory.json"
ANALYSIS_FILENAMES_V1 = (
    "aligned-resource-forecast.encoder.pt",
    "player-shuffled-resource-forecast.encoder.pt",
    "aligned-resource-forecast.receipt.json",
    "player-shuffled-resource-forecast.receipt.json",
    "probe-representation-matrices.npz",
    "probe-representation-matrices.metadata.json",
    "pilot-result.json",
    "independent-verification.json",
)
EXPECTED_CATEGORY_COUNTS_V1 = {
    "protocol": 1,
    "manifest": 1,
    "history_scan_receipt": 1,
    "gather_transport_marker": 1,
    "gather_receipt": 1,
    "dispatch_status": 2,
    "worker_status": 12,
    "worker_log": 12,
    "training_json": 144,
    "model_pt": 432,
    "label_json": 432,
    "probe_json": 432,
    "trajectory_json": 288,
    "trajectory_npz": 288,
    "encoder_pt": 2,
    "encoder_receipt": 2,
    "matrix_npz": 1,
    "matrix_metadata": 1,
    "pilot_result": 1,
    "verification": 1,
    "postprocess_status": 1,
}
AnalysisRunnerV1 = Callable[[SimpleNamespace], dict[str, Any]]
VerifierRunnerV1 = Callable[[SimpleNamespace], dict[str, Any]]
RetentionCopierV1 = Callable[..., dict[str, Any]]
RuntimeValidatorV1 = Callable[[Path, Path, str], None]


class LearnedResourceForecastPostprocessV1Error(RuntimeError):
    """The one-shot postprocess inputs, stage, or retention are not exact."""


def _load_script_module(name: str, filename: str):
    path = REPOSITORY / "scripts" / filename
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise LearnedResourceForecastPostprocessV1Error(
            f"cannot load registered postprocess dependency: {path}"
        )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_prepare_module():
    return _load_script_module(
        "acfqp_u002_prepare_for_postprocess",
        "prepare_learned_resource_forecast_campaign_u002.py",
    )


def _load_history_scan_module():
    return _load_script_module(
        "acfqp_u002_history_for_postprocess",
        "scan_learned_resource_forecast_history_u002.py",
    )


def _load_gather_module():
    return _load_script_module(
        "acfqp_u002_gather_for_postprocess",
        "gather_learned_resource_forecast_evidence_u002.py",
    )


def _default_analysis_runner(args: SimpleNamespace) -> dict[str, Any]:
    module = _load_script_module(
        "acfqp_u002_analysis_for_postprocess",
        "run_learned_resource_forecast_analysis_u002.py",
    )
    return module._run(args)


def _default_verifier_runner(args: SimpleNamespace) -> dict[str, Any]:
    module = _load_script_module(
        "acfqp_u002_verifier_for_postprocess",
        "verify_learned_resource_forecast_analysis_u002.py",
    )
    return module._verify(args)


def _default_runtime_validator(
    protocol_path: Path, manifest_path: Path, device: str
) -> None:
    module = _load_script_module(
        "acfqp_u002_analysis_runtime_for_postprocess",
        "run_learned_resource_forecast_analysis_u002.py",
    )
    protocol = module._load_protocol(protocol_path)
    manifest = module._load_manifest(manifest_path, protocol)
    module._validate_analysis_runtime(manifest, requested_device=device)
    import torch

    requested = torch.device(device)
    if (
        requested.type != "cuda"
        or not torch.cuda.is_available()
        or requested.index is None
        or requested.index >= torch.cuda.device_count()
    ):
        raise LearnedResourceForecastPostprocessV1Error(
            "central analysis CUDA device is unavailable"
        )


def _read_object(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise LearnedResourceForecastPostprocessV1Error(
            f"cannot read {label} as one JSON object: {path}"
        ) from error
    if type(value) is not dict:
        raise LearnedResourceForecastPostprocessV1Error(
            f"{label} must contain one JSON object"
        )
    return value


def _read_jsonl(path: Path, label: str) -> list[dict[str, Any]]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as error:
        raise LearnedResourceForecastPostprocessV1Error(
            f"cannot read {label}: {path}"
        ) from error
    rows: list[dict[str, Any]] = []
    for line in lines:
        try:
            value = json.loads(line)
        except json.JSONDecodeError as error:
            raise LearnedResourceForecastPostprocessV1Error(
                f"{label} contains malformed JSONL"
            ) from error
        if type(value) is not dict:
            raise LearnedResourceForecastPostprocessV1Error(
                f"{label} contains a non-object row"
            )
        rows.append(value)
    if not rows:
        raise LearnedResourceForecastPostprocessV1Error(f"{label} is empty")
    return rows


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
            raise LearnedResourceForecastPostprocessV1Error(
                "postprocess status already exists; the attempt is consumed"
            ) from error
        return self

    def emit(self, event: dict[str, Any]) -> None:
        if self._fd is None:
            raise LearnedResourceForecastPostprocessV1Error(
                "postprocess status is not open"
            )
        view = memoryview(canonical_json_bytes(event) + b"\n")
        while view:
            view = view[os.write(self._fd, view) :]
        os.fsync(self._fd)

    def __exit__(self, _type, _value, _traceback) -> None:
        if self._fd is not None:
            os.close(self._fd)
            self._fd = None


def _worker_artifact_map(worker: dict[str, Any]) -> dict[str, str]:
    artifacts: dict[str, str] = {}
    for job in worker["policy_training_jobs"]:
        artifacts[job["result_filename"]] = "training_json"
        for filename in job["checkpoint_filenames"]:
            artifacts[filename] = "model_pt"
    for job in worker["player_evidence_jobs"]:
        artifacts[job["label_filename"]] = "label_json"
        artifacts[job["probe_filename"]] = "probe_json"
        if job["split"] == "TRAIN":
            artifacts[job["trajectory_metadata_filename"]] = "trajectory_json"
            artifacts[job["trajectory_array_filename"]] = "trajectory_npz"
    if len(artifacts) not in (330, 348):
        raise LearnedResourceForecastPostprocessV1Error(
            "worker artifact allowlist no longer closes its registered roster"
        )
    return artifacts


def _require_exact_directory(
    path: Path, expected_names: set[str], label: str
) -> None:
    if not path.is_dir():
        raise LearnedResourceForecastPostprocessV1Error(f"{label} is not a directory")
    entries = list(path.iterdir())
    if (
        any(not entry.is_file() for entry in entries)
        or {entry.name for entry in entries} != expected_names
    ):
        raise LearnedResourceForecastPostprocessV1Error(
            f"{label} contains missing, duplicate, foreign, or non-file artifacts"
        )


def _validate_worker_status(
    path: Path, *, phase: str, worker: dict[str, Any]
) -> None:
    rows = _read_jsonl(path, "worker status stream")
    jobs = (
        worker["policy_training_jobs"]
        if phase == "training"
        else worker["player_evidence_jobs"]
    )
    expected_events: list[str] = ["WORKER_STARTED"]
    for _job in jobs:
        expected_events.extend(("JOB_STARTED", "JOB_COMPLETED"))
    expected_events.append("WORKER_COMPLETED")
    if (
        [row.get("event") for row in rows] != expected_events
        or any(
            row.get("phase") != phase or row.get("worker") != worker["worker"]
            for row in rows
        )
        or rows[-1].get("completed_job_count") != len(jobs)
    ):
        raise LearnedResourceForecastPostprocessV1Error(
            "worker status lifecycle is not exactly complete"
        )
    for ordinal, job in enumerate(jobs):
        started = rows[1 + 2 * ordinal]
        completed = rows[2 + 2 * ordinal]
        if (
            started.get("job_ordinal") != ordinal
            or completed.get("job_ordinal") != ordinal
            or started.get("execution_id") != job["execution_id"]
            or completed.get("execution_id") != job["execution_id"]
            or started.get("preexecution_identity_check_only") is not False
            or completed.get("completed_job_count") != ordinal + 1
            or completed.get("expected_job_count") != len(jobs)
        ):
            raise LearnedResourceForecastPostprocessV1Error(
                "worker status job roster is missing, reordered, or foreign"
            )


def _validate_dispatch_status(
    path: Path,
    *,
    phase: str,
    manifest: dict[str, Any],
    fixed: dict[str, str],
) -> None:
    rows = _read_jsonl(path, "phase dispatch status")
    if (
        [row.get("event") for row in rows]
        != [
            "GLOBAL_PRECHECK_COMPLETED",
            "DISPATCH_STARTED",
            *("WORKER_DISPATCHED" for _ in range(6)),
            "DISPATCH_COMPLETED",
        ]
        or any(row.get("phase") != phase for row in rows)
        or rows[0].get("prechecked_worker_count") != 6
        or rows[0].get("filesystem_mutation_before_precheck_completed") is not False
        or rows[-1].get("dispatched_worker_count") != 6
        or rows[-1].get("worker_execution_completed") is not False
    ):
        raise LearnedResourceForecastPostprocessV1Error(
            "phase dispatch status is not exactly complete"
        )
    for worker, row in zip(manifest["workers"], rows[2:-1], strict=True):
        status_name = worker[
            "policy_training_status_stream"
            if phase == "training"
            else "player_evidence_status_stream"
        ]
        if (
            row.get("worker") != worker["worker"]
            or row.get("host_alias") != worker["host_alias"]
            or row.get("expected_hostname") != worker["expected_hostname"]
            or row.get("device") != worker["device"]
            or type(row.get("remote_pid")) is not int
            or row["remote_pid"] <= 0
            or row.get("worker_results_root")
            != str(Path(fixed["results_root"]) / f"worker-{worker['worker']}")
            or row.get("worker_status_stream")
            != str(Path(fixed["status_root"]) / status_name)
            or row.get("worker_log")
            != str(Path(fixed["log_root"]) / f"worker-{worker['worker']}-{phase}.log")
        ):
            raise LearnedResourceForecastPostprocessV1Error(
                "phase dispatch worker row differs from the manifest"
            )


def _validate_worker_log(
    path: Path, *, phase: str, worker: dict[str, Any], results_root: Path
) -> None:
    try:
        lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line]
        summary = json.loads(lines[-1])
    except (OSError, IndexError, json.JSONDecodeError) as error:
        raise LearnedResourceForecastPostprocessV1Error(
            f"worker log has no final JSON summary: {path}"
        ) from error
    expected_count = 24 if phase == "training" else 72
    if (
        type(summary) is not dict
        or summary.get("success") is not True
        or summary.get("phase") != phase
        or summary.get("worker") != worker["worker"]
        or summary.get("completed_job_count") != expected_count
        or Path(str(summary.get("results_root", ""))).resolve()
        != results_root.resolve()
    ):
        raise LearnedResourceForecastPostprocessV1Error(
            "worker log final summary differs from the completed worker"
        )


def _validate_prerequisites(
    *, protocol: dict[str, Any], manifest: dict[str, Any]
) -> tuple[list[Path], list[tuple[Path, str, Path]]]:
    fixed = manifest["fixed_paths"]
    results_root = Path(fixed["results_root"])
    status_root = Path(fixed["status_root"])
    log_root = Path(fixed["log_root"])
    expected_worker_dirs = [results_root / f"worker-{index}" for index in range(6)]
    if (
        not results_root.is_dir()
        or {path.name for path in results_root.iterdir()}
        != {path.name for path in expected_worker_dirs}
        or any(not path.is_dir() for path in expected_worker_dirs)
    ):
        raise LearnedResourceForecastPostprocessV1Error(
            "gathered results root is not exactly six distinct worker directories"
        )
    source_entries: list[tuple[Path, str, Path]] = []
    category_counts: dict[str, int] = {}
    for worker, worker_dir in zip(
        manifest["workers"], expected_worker_dirs, strict=True
    ):
        artifacts = _worker_artifact_map(worker)
        _require_exact_directory(
            worker_dir, set(artifacts), f"worker-{worker['worker']} result directory"
        )
        for filename, category in artifacts.items():
            source_entries.append(
                (worker_dir / filename, category, Path("workers") / worker_dir.name / filename)
            )

    expected_status_names = {
        worker[name]
        for worker in manifest["workers"]
        for name in (
            "policy_training_status_stream",
            "player_evidence_status_stream",
        )
    }
    _require_exact_directory(status_root, expected_status_names, "worker status root")
    expected_log_names = {
        f"worker-{worker['worker']}-{phase}.log"
        for worker in manifest["workers"]
        for phase in ("training", "evidence")
    }
    _require_exact_directory(log_root, expected_log_names, "worker log root")
    for worker in manifest["workers"]:
        worker_dir = results_root / f"worker-{worker['worker']}"
        for phase, status_key in (
            ("training", "policy_training_status_stream"),
            ("evidence", "player_evidence_status_stream"),
        ):
            status_path = status_root / worker[status_key]
            log_path = log_root / f"worker-{worker['worker']}-{phase}.log"
            _validate_worker_status(status_path, phase=phase, worker=worker)
            _validate_worker_log(
                log_path, phase=phase, worker=worker, results_root=worker_dir
            )
            source_entries.append(
                (status_path, "worker_status", Path("status") / status_path.name)
            )
            source_entries.append((log_path, "worker_log", Path("logs") / log_path.name))

    for phase, key in (
        ("training", "training_dispatch_status"),
        ("evidence", "evidence_dispatch_status"),
    ):
        dispatch_path = Path(fixed[key])
        _validate_dispatch_status(
            dispatch_path, phase=phase, manifest=manifest, fixed=fixed
        )
        source_entries.append(
            (dispatch_path, "dispatch_status", Path("dispatch") / dispatch_path.name)
        )

    authority = (
        (Path(fixed["protocol"]), "protocol"),
        (Path(fixed["manifest"]), "manifest"),
        (Path(fixed["history_scan_receipt"]), "history_scan_receipt"),
        (Path(fixed["gather_transport_marker"]), "gather_transport_marker"),
        (Path(fixed["gather_receipt"]), "gather_receipt"),
    )
    for path, category in authority:
        if not path.is_file():
            raise LearnedResourceForecastPostprocessV1Error(
                "retained authority input is missing"
            )
        source_entries.append((path, category, Path("authority") / path.name))
    for _path, category, _relative in source_entries:
        category_counts[category] = category_counts.get(category, 0) + 1
    expected_preanalysis_counts = {
        key: value
        for key, value in EXPECTED_CATEGORY_COUNTS_V1.items()
        if key not in {
            "encoder_pt",
            "encoder_receipt",
            "matrix_npz",
            "matrix_metadata",
            "pilot_result",
            "verification",
            "postprocess_status",
        }
    }
    if category_counts != expected_preanalysis_counts:
        raise LearnedResourceForecastPostprocessV1Error(
            "preanalysis artifact category counts do not close exactly"
        )
    return expected_worker_dirs, source_entries


def _analysis_entries(analysis_root: Path) -> list[tuple[Path, str, Path]]:
    categories = {
        "aligned-resource-forecast.encoder.pt": "encoder_pt",
        "player-shuffled-resource-forecast.encoder.pt": "encoder_pt",
        "aligned-resource-forecast.receipt.json": "encoder_receipt",
        "player-shuffled-resource-forecast.receipt.json": "encoder_receipt",
        "probe-representation-matrices.npz": "matrix_npz",
        "probe-representation-matrices.metadata.json": "matrix_metadata",
        "pilot-result.json": "pilot_result",
        "independent-verification.json": "verification",
    }
    _require_exact_directory(analysis_root, set(categories), "analysis output root")
    return [
        (analysis_root / name, category, Path("analysis") / name)
        for name, category in categories.items()
    ]


def _copy_retained(
    *,
    entries: list[tuple[Path, str, Path]],
    retained_root: Path,
    protocol: dict[str, Any],
) -> dict[str, Any]:
    if retained_root.exists():
        raise LearnedResourceForecastPostprocessV1Error(
            "retained root already exists; the retention identity is consumed"
        )
    retained_root.mkdir(parents=False)
    inventory_rows: list[dict[str, Any]] = []
    category_counts: dict[str, int] = {}
    for source, category, relative in entries:
        if not source.is_file():
            raise LearnedResourceForecastPostprocessV1Error(
                f"retention source disappeared: {source}"
            )
        target = retained_root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            raise LearnedResourceForecastPostprocessV1Error(
                "retention destination collision changed the exact inventory"
            )
        shutil.copy2(source, target)
        inventory_rows.append(
            {
                "category": category,
                "source_path": str(source),
                "retained_relative_path": relative.as_posix(),
                "size_bytes": target.stat().st_size,
            }
        )
        category_counts[category] = category_counts.get(category, 0) + 1
    if category_counts != EXPECTED_CATEGORY_COUNTS_V1:
        raise LearnedResourceForecastPostprocessV1Error(
            "retention category counts differ from the registered inventory"
        )
    inventory = {
        "schema": SCHEMA_V1,
        "protocol_id": protocol["protocol_id"],
        "source_commit": protocol["source_commit"],
        "pilot_execution_identity": protocol["pilot_execution_identity"],
        "retention_complete": True,
        "category_counts": category_counts,
        "retained_artifact_count_excluding_inventory": len(inventory_rows),
        "physical_file_count_including_inventory": len(inventory_rows) + 1,
        "entries": inventory_rows,
    }
    inventory_path = retained_root / INVENTORY_FILENAME_V1
    write_exclusive_bytes_v1(inventory_path, canonical_json_bytes(inventory))
    actual_files = {
        path.relative_to(retained_root).as_posix()
        for path in retained_root.rglob("*")
        if path.is_file()
    }
    expected_files = {
        row["retained_relative_path"] for row in inventory_rows
    } | {INVENTORY_FILENAME_V1}
    if actual_files != expected_files:
        raise LearnedResourceForecastPostprocessV1Error(
            "retained tree contains a missing or foreign physical file"
        )
    return inventory


def _run(
    args: argparse.Namespace,
    *,
    analysis_runner: AnalysisRunnerV1 | None = None,
    verifier_runner: VerifierRunnerV1 | None = None,
    retention_copier: RetentionCopierV1 | None = None,
    runtime_validator: RuntimeValidatorV1 | None = None,
) -> dict[str, Any]:
    prepare = _load_prepare_module()
    protocol_path = require_path_outside_repository_v1(
        repository=REPOSITORY, path=args.protocol, label="ratified U002 protocol"
    )
    manifest_path = require_path_outside_repository_v1(
        repository=REPOSITORY, path=args.manifest, label="U002 launch manifest"
    )
    history_path = require_path_outside_repository_v1(
        repository=REPOSITORY,
        path=args.history_scan_receipt,
        label="U002 history-scan receipt",
    )
    gather_path = require_path_outside_repository_v1(
        repository=REPOSITORY,
        path=args.gather_receipt,
        label="U002 gather receipt",
    )
    protocol = validate_ratified_learned_resource_forecast_protocol_v1(
        _read_object(protocol_path, "ratified U002 protocol")
    )
    manifest = _read_object(manifest_path, "U002 launch manifest")
    if manifest != prepare.build_launch_manifest_v1(protocol):
        raise LearnedResourceForecastPostprocessV1Error(
            "launch manifest does not replay from the ratified protocol"
        )
    fixed = manifest["fixed_paths"]
    analysis_root = Path(fixed["analysis_root"]).resolve()
    retained_root = Path(fixed["retained_root"]).resolve()
    status_path = Path(fixed["postprocess_status"]).resolve()
    source_commit = bound_clean_source_commit_v1(REPOSITORY)
    if (
        source_commit != protocol["source_commit"]
        or REPOSITORY.resolve() != Path(fixed["source_checkout"]).resolve()
        or protocol_path != Path(fixed["protocol"]).resolve()
        or manifest_path != Path(fixed["manifest"]).resolve()
        or history_path != Path(fixed["history_scan_receipt"]).resolve()
        or gather_path != Path(fixed["gather_receipt"]).resolve()
        or socket.gethostname()
        != manifest["central_analysis"]["expected_hostname"]
        or args.analysis_device != manifest["central_analysis"]["device"]
        or args.verifier_device != manifest["central_analysis"]["device"]
    ):
        raise LearnedResourceForecastPostprocessV1Error(
            "postprocess source, paths, host, or devices differ from the manifest"
        )
    history = _load_history_scan_module()
    history.validate_history_scan_receipt_v1(
        _read_object(history_path, "U002 history-scan receipt"), protocol, manifest
    )
    gather = _load_gather_module()
    gather.validate_gather_receipt_v1(
        _read_object(gather_path, "U002 gather receipt"), protocol, manifest
    )
    if analysis_root.exists() or retained_root.exists() or status_path.exists():
        raise LearnedResourceForecastPostprocessV1Error(
            "analysis, retained, or status target already exists; the attempt is consumed"
        )

    run_analysis = analysis_runner or _default_analysis_runner
    run_verifier = verifier_runner or _default_verifier_runner
    copy_retained = retention_copier or _copy_retained
    validate_runtime = runtime_validator or _default_runtime_validator
    validate_runtime(protocol_path, manifest_path, args.analysis_device)
    worker_dirs, retention_entries = _validate_prerequisites(
        protocol=protocol, manifest=manifest
    )
    with _ExclusiveStatusStreamV1(status_path) as status:
        status.emit(
            {
                "event": "POSTPROCESS_STARTED",
                "protocol_id": protocol["protocol_id"],
                "source_commit": source_commit,
                "host": socket.gethostname(),
            }
        )
        try:
            status.emit(
                {
                    "event": "PREREQUISITES_COMPLETED",
                    "worker_directory_count": 6,
                    "worker_status_count": 12,
                    "worker_log_count": 12,
                }
            )
            analysis_root.mkdir(parents=False)
            common = {
                "protocol": protocol_path,
                "manifest": manifest_path,
                "device": args.analysis_device,
            }
            stages = [
                (
                    "FIT_ENCODERS",
                    SimpleNamespace(
                        operation="fit-encoders",
                        trajectory_dir=worker_dirs,
                        output_dir=analysis_root,
                        **common,
                    ),
                ),
                (
                    "ENCODE_PROBES",
                    SimpleNamespace(
                        operation="encode-probes",
                        probe_dir=worker_dirs,
                        aligned_encoder=analysis_root
                        / "aligned-resource-forecast.encoder.pt",
                        shuffled_encoder=analysis_root
                        / "player-shuffled-resource-forecast.encoder.pt",
                        output_dir=analysis_root,
                        **common,
                    ),
                ),
                (
                    "EVALUATE",
                    SimpleNamespace(
                        operation="evaluate",
                        status_dir=[Path(fixed["status_root"])],
                        worker_result_dir=worker_dirs,
                        matrix=analysis_root / "probe-representation-matrices.npz",
                        matrix_metadata=analysis_root
                        / "probe-representation-matrices.metadata.json",
                        encoder_receipt_dir=analysis_root,
                        label_dir=worker_dirs,
                        output=analysis_root / "pilot-result.json",
                        **common,
                    ),
                ),
            ]
            for stage_name, stage_args in stages:
                status.emit({"event": "STAGE_STARTED", "stage": stage_name})
                summary = run_analysis(stage_args)
                if summary.get("success") is not True:
                    raise LearnedResourceForecastPostprocessV1Error(
                        f"analysis stage returned no exact success: {stage_name}"
                    )
                status.emit({"event": "STAGE_COMPLETED", "stage": stage_name})
            status.emit(
                {"event": "STAGE_STARTED", "stage": "INDEPENDENT_VERIFIER"}
            )
            verification_summary = run_verifier(
                SimpleNamespace(
                    protocol=protocol_path,
                    manifest=manifest_path,
                    status_dir=[Path(fixed["status_root"])],
                    trajectory_dir=worker_dirs,
                    probe_dir=worker_dirs,
                    label_dir=worker_dirs,
                    encoder_dir=analysis_root,
                    worker_result_dir=worker_dirs,
                    matrix=analysis_root / "probe-representation-matrices.npz",
                    matrix_metadata=analysis_root
                    / "probe-representation-matrices.metadata.json",
                    result=analysis_root / "pilot-result.json",
                    output=analysis_root / "independent-verification.json",
                    device=args.verifier_device,
                )
            )
            if verification_summary.get("success") is not True:
                raise LearnedResourceForecastPostprocessV1Error(
                    "independent verifier returned no exact success"
                )
            status.emit(
                {"event": "STAGE_COMPLETED", "stage": "INDEPENDENT_VERIFIER"}
            )
            retention_entries.extend(_analysis_entries(analysis_root))
            status.emit(
                {
                    "event": "ANALYSIS_VERIFICATION_COMPLETED_RETENTION_READY",
                    "retention_source_count_before_closed_status": len(
                        retention_entries
                    ),
                    "retention_complete": False,
                }
            )
        except Exception as error:
            status.emit(
                {
                    "event": "POSTPROCESS_FAILED",
                    "failure_kind": type(error).__name__,
                    "failure_message": str(error),
                }
            )
            raise
    retention_entries.append(
        (
            status_path,
            "postprocess_status",
            Path("status") / status_path.name,
        )
    )
    inventory = copy_retained(
        entries=retention_entries,
        retained_root=retained_root,
        protocol=protocol,
    )
    return {
        "success": True,
        "protocol_id": protocol["protocol_id"],
        "analysis_root": str(analysis_root),
        "retained_root": str(retained_root),
        "postprocess_status": str(status_path),
        "retained_artifact_count_excluding_inventory": inventory[
            "retained_artifact_count_excluding_inventory"
        ],
        "physical_file_count_including_inventory": inventory[
            "physical_file_count_including_inventory"
        ],
        "PROVISIONAL_DESIGN_SIGNAL_GATE": _read_object(
            analysis_root / "pilot-result.json", "pilot result"
        ).get("PROVISIONAL_DESIGN_SIGNAL_GATE"),
        "independent_verification": _read_object(
            analysis_root / "independent-verification.json",
            "independent verification",
        ).get("valid"),
    }


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--history-scan-receipt", type=Path, required=True)
    parser.add_argument("--gather-receipt", type=Path, required=True)
    parser.add_argument("--analysis-device", default="cuda:0")
    parser.add_argument("--verifier-device", default="cuda:0")
    return parser.parse_args()


def main() -> int:
    try:
        summary = _run(_arguments())
    except (
        LearnedResourceForecastPostprocessV1Error,
        LearnedResourceForecastProtocolV1Error,
        ScienceExecutionIOV1Error,
    ) as error:
        raise SystemExit(str(error)) from error
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
