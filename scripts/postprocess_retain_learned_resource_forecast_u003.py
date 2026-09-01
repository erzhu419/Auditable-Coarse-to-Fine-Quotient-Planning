#!/usr/bin/env python3
"""Run U003 dual-authority analysis, verification, and server-side retention."""

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
from acfqp.science.learned_resource_forecast_evidence_successor_protocol_v1 import (
    LearnedResourceForecastEvidenceSuccessorProtocolV1Error,
    validate_ratified_learned_resource_forecast_evidence_successor_protocol_v1,
)
from acfqp.science.learned_resource_forecast_protocol_v1 import (
    LearnedResourceForecastProtocolV1Error,
    validate_ratified_learned_resource_forecast_protocol_v1,
)


REPOSITORY = Path(__file__).resolve().parents[1]
SCHEMA_V1 = (
    "acfqp.science.learned_resource_forecast_postprocess_retention.u003.v1"
)
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

PROVENANCE_U002_TRAINING_V1 = "READ_ONLY_U002_TRAINING_AUTHORITY"
PROVENANCE_U003_EVIDENCE_V1 = "FRESH_U003_EVIDENCE_AUTHORITY"
PROVENANCE_GATHER_V1 = "U003_DUAL_AUTHORITY_GATHER"
PROVENANCE_FAILED_U002_EVIDENCE_V1 = (
    "U002_FAILED_EVIDENCE_DISPATCH_FAILURE_HISTORY_INELIGIBLE"
)
PROVENANCE_ANALYSIS_V1 = "U003_ANALYSIS_DERIVED_FROM_DUAL_AUTHORITY"
PROVENANCE_POSTPROCESS_V1 = "U003_POSTPROCESS_STATUS"

EXPECTED_CATEGORY_COUNTS_V1 = {
    "predecessor_protocol": 1,
    "predecessor_manifest": 1,
    "successor_protocol": 1,
    "successor_manifest": 1,
    "successor_history_scan_receipt": 1,
    "gather_transport_marker": 1,
    "gather_receipt": 1,
    "predecessor_training_dispatch_status": 1,
    "ineligible_predecessor_failed_evidence_dispatch": 1,
    "successor_evidence_dispatch_status": 1,
    "predecessor_training_worker_status": 6,
    "predecessor_training_worker_log": 6,
    "successor_evidence_worker_status": 6,
    "successor_evidence_worker_log": 6,
    "predecessor_training_json": 144,
    "predecessor_model_pt": 432,
    "successor_label_json": 432,
    "successor_probe_json": 432,
    "successor_trajectory_json": 288,
    "successor_trajectory_npz": 288,
    "successor_encoder_pt": 2,
    "successor_encoder_receipt": 2,
    "successor_matrix_npz": 1,
    "successor_matrix_metadata": 1,
    "successor_pilot_result": 1,
    "successor_verification": 1,
    "postprocess_status": 1,
}
EXPECTED_PROVENANCE_COUNTS_V1 = {
    PROVENANCE_U002_TRAINING_V1: 591,
    PROVENANCE_U003_EVIDENCE_V1: 1456,
    PROVENANCE_GATHER_V1: 2,
    PROVENANCE_FAILED_U002_EVIDENCE_V1: 1,
    PROVENANCE_ANALYSIS_V1: 8,
    PROVENANCE_POSTPROCESS_V1: 1,
}

RetentionEntryV1 = tuple[Path, str, str, Path]
AnalysisRunnerV1 = Callable[[SimpleNamespace], dict[str, Any]]
VerifierRunnerV1 = Callable[[SimpleNamespace], dict[str, Any]]
RetentionCopierV1 = Callable[..., dict[str, Any]]
RuntimeValidatorV1 = Callable[[Path, Path, Path, Path, str], None]


class LearnedResourceForecastPostprocessU003V1Error(RuntimeError):
    """The U002-training/U003-evidence postprocess closure is not exact."""


def _load_script_module(name: str, filename: str):
    path = REPOSITORY / "scripts" / filename
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise LearnedResourceForecastPostprocessU003V1Error(
            f"cannot load registered U003 postprocess dependency: {path}"
        )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_predecessor_prepare_module():
    return _load_script_module(
        "acfqp_u002_prepare_for_u003_postprocess",
        "prepare_learned_resource_forecast_campaign_u002.py",
    )


def _load_successor_prepare_module():
    return _load_script_module(
        "acfqp_u003_prepare_for_u003_postprocess",
        "prepare_learned_resource_forecast_evidence_successor_u003.py",
    )


def _load_history_scan_module():
    return _load_script_module(
        "acfqp_u003_history_for_u003_postprocess",
        "scan_learned_resource_forecast_history_u003.py",
    )


def _load_gather_module():
    return _load_script_module(
        "acfqp_u003_gather_for_u003_postprocess",
        "gather_learned_resource_forecast_evidence_u003.py",
    )


def _default_analysis_runner(args: SimpleNamespace) -> dict[str, Any]:
    module = _load_script_module(
        "acfqp_u003_analysis_for_u003_postprocess",
        "run_learned_resource_forecast_analysis_u003.py",
    )
    return module._run(args)


def _default_verifier_runner(args: SimpleNamespace) -> dict[str, Any]:
    module = _load_script_module(
        "acfqp_u003_verifier_for_u003_postprocess",
        "verify_learned_resource_forecast_analysis_u003.py",
    )
    return module._verify(args)


def _default_runtime_validator(
    predecessor_protocol_path: Path,
    predecessor_manifest_path: Path,
    successor_protocol_path: Path,
    successor_manifest_path: Path,
    device: str,
) -> None:
    module = _load_script_module(
        "acfqp_u003_analysis_runtime_for_u003_postprocess",
        "run_learned_resource_forecast_analysis_u003.py",
    )
    args = SimpleNamespace(
        predecessor_protocol=predecessor_protocol_path,
        predecessor_manifest=predecessor_manifest_path,
        protocol=successor_protocol_path,
        manifest=successor_manifest_path,
    )
    predecessor, successor = module._load_protocols(args)
    dual_manifest = module._validate_dual_manifests(
        _read_object(predecessor_manifest_path, "U002 predecessor manifest"),
        _read_object(successor_manifest_path, "U003 successor manifest"),
        predecessor_protocol=predecessor,
        successor_protocol=successor,
    )
    module._BASE._validate_analysis_runtime(  # noqa: SLF001
        dual_manifest, requested_device=device
    )
    import torch

    requested = torch.device(device)
    if (
        requested.type != "cuda"
        or not torch.cuda.is_available()
        or requested.index is None
        or requested.index >= torch.cuda.device_count()
    ):
        raise LearnedResourceForecastPostprocessU003V1Error(
            "central U003 analysis CUDA device is unavailable"
        )


def _read_object(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise LearnedResourceForecastPostprocessU003V1Error(
            f"cannot read {label} as one JSON object: {path}"
        ) from error
    if type(value) is not dict:
        raise LearnedResourceForecastPostprocessU003V1Error(
            f"{label} must contain one JSON object"
        )
    return value


def _read_jsonl(path: Path, label: str) -> list[dict[str, Any]]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as error:
        raise LearnedResourceForecastPostprocessU003V1Error(
            f"cannot read {label}: {path}"
        ) from error
    rows: list[dict[str, Any]] = []
    for line in lines:
        try:
            row = json.loads(line)
        except json.JSONDecodeError as error:
            raise LearnedResourceForecastPostprocessU003V1Error(
                f"{label} contains malformed JSONL"
            ) from error
        if type(row) is not dict:
            raise LearnedResourceForecastPostprocessU003V1Error(
                f"{label} contains a non-object row"
            )
        rows.append(row)
    if not rows:
        raise LearnedResourceForecastPostprocessU003V1Error(f"{label} is empty")
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
            raise LearnedResourceForecastPostprocessU003V1Error(
                "U003 postprocess status already exists; the attempt is consumed"
            ) from error
        return self

    def emit(self, event: dict[str, Any]) -> None:
        if self._fd is None:
            raise LearnedResourceForecastPostprocessU003V1Error(
                "U003 postprocess status is not open"
            )
        view = memoryview(canonical_json_bytes(event) + b"\n")
        while view:
            view = view[os.write(self._fd, view) :]
        os.fsync(self._fd)

    def __exit__(self, _type, _value, _traceback) -> None:
        if self._fd is not None:
            os.close(self._fd)
            self._fd = None


def _predecessor_artifact_map(worker: dict[str, Any]) -> dict[str, str]:
    artifacts: dict[str, str] = {}
    for job in worker["policy_training_jobs"]:
        artifacts[job["result_filename"]] = "predecessor_training_json"
        for filename in job["checkpoint_filenames"]:
            artifacts[filename] = "predecessor_model_pt"
    if len(artifacts) != 96:
        raise LearnedResourceForecastPostprocessU003V1Error(
            "U002 worker training artifact allowlist no longer closes at 96"
        )
    return artifacts


def _successor_artifact_map(worker: dict[str, Any]) -> dict[str, str]:
    artifacts: dict[str, str] = {}
    for job in worker["player_evidence_jobs"]:
        artifacts[job["label_filename"]] = "successor_label_json"
        artifacts[job["probe_filename"]] = "successor_probe_json"
        if job["split"] == "TRAIN":
            artifacts[job["trajectory_metadata_filename"]] = (
                "successor_trajectory_json"
            )
            artifacts[job["trajectory_array_filename"]] = "successor_trajectory_npz"
    if len(artifacts) not in (234, 252):
        raise LearnedResourceForecastPostprocessU003V1Error(
            "U003 worker evidence artifact allowlist changed"
        )
    return artifacts


def _require_exact_directory(path: Path, expected_names: set[str], label: str) -> None:
    if not path.is_dir():
        raise LearnedResourceForecastPostprocessU003V1Error(
            f"{label} is not a directory"
        )
    entries = list(path.iterdir())
    if (
        any(not entry.is_file() for entry in entries)
        or {entry.name for entry in entries} != expected_names
    ):
        raise LearnedResourceForecastPostprocessU003V1Error(
            f"{label} contains missing, duplicate, foreign, or non-file artifacts"
        )


def _validate_worker_status(
    path: Path, *, phase: str, worker_index: int, jobs: list[dict[str, Any]]
) -> None:
    rows = _read_jsonl(path, f"{phase} worker status")
    expected_events: list[str] = ["WORKER_STARTED"]
    for _job in jobs:
        expected_events.extend(("JOB_STARTED", "JOB_COMPLETED"))
    expected_events.append("WORKER_COMPLETED")
    if (
        [row.get("event") for row in rows] != expected_events
        or any(
            row.get("phase") != phase or row.get("worker") != worker_index
            for row in rows
        )
        or rows[-1].get("completed_job_count") != len(jobs)
    ):
        raise LearnedResourceForecastPostprocessU003V1Error(
            f"{phase} worker status lifecycle is not exactly complete"
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
            raise LearnedResourceForecastPostprocessU003V1Error(
                f"{phase} worker status roster is missing, reordered, or foreign"
            )


def _validate_worker_log(
    path: Path,
    *,
    phase: str,
    worker_index: int,
    expected_count: int,
    results_root: Path,
) -> None:
    try:
        lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line]
        summary = json.loads(lines[-1])
    except (OSError, IndexError, json.JSONDecodeError) as error:
        raise LearnedResourceForecastPostprocessU003V1Error(
            f"{phase} worker log has no final JSON summary: {path}"
        ) from error
    if (
        type(summary) is not dict
        or summary.get("success") is not True
        or summary.get("phase") != phase
        or summary.get("worker") != worker_index
        or summary.get("completed_job_count") != expected_count
        or Path(str(summary.get("results_root", ""))).resolve()
        != results_root.resolve()
    ):
        raise LearnedResourceForecastPostprocessU003V1Error(
            f"{phase} worker log final summary differs from its completed worker"
        )


def _validate_dispatch_status(
    path: Path,
    *,
    phase: str,
    manifest: dict[str, Any],
    fixed: dict[str, str],
    successor: bool,
) -> None:
    rows = _read_jsonl(path, f"{phase} dispatch status")
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
        raise LearnedResourceForecastPostprocessU003V1Error(
            f"{phase} dispatch status is not exactly complete"
        )
    for worker, row in zip(manifest["workers"], rows[2:-1], strict=True):
        status_name = worker[
            "player_evidence_status_stream"
            if successor
            else "policy_training_status_stream"
        ]
        expected_root = Path(fixed["results_root"]) / f"worker-{worker['worker']}"
        if (
            row.get("worker") != worker["worker"]
            or row.get("host_alias") != worker["host_alias"]
            or row.get("expected_hostname") != worker["expected_hostname"]
            or row.get("device") != worker["device"]
            or type(row.get("remote_pid")) is not int
            or row["remote_pid"] <= 0
            or row.get("worker_results_root") != str(expected_root)
            or row.get("worker_status_stream")
            != str(Path(fixed["status_root"]) / status_name)
            or row.get("worker_log")
            != str(
                Path(fixed["log_root"])
                / f"worker-{worker['worker']}-{phase}.log"
            )
            or (
                successor
                and row.get("predecessor_snapshot_root")
                != worker["predecessor_snapshot_root"]
            )
        ):
            raise LearnedResourceForecastPostprocessU003V1Error(
                f"{phase} dispatch worker row differs from its manifest"
            )
    if successor and (
        rows[0].get("parent_training_closure_all_passed") is not True
        or rows[1].get("u002_failed_evidence_dispatch_eligible") is not False
    ):
        raise LearnedResourceForecastPostprocessU003V1Error(
            "U003 dispatch did not preserve its predecessor/ineligible boundary"
        )


def _validate_ineligible_failed_dispatch(path: Path) -> None:
    rows = _read_jsonl(path, "ineligible failed U002 evidence dispatch")
    if (
        [row.get("event") for row in rows]
        != [
            "GLOBAL_PRECHECK_COMPLETED",
            "DISPATCH_STARTED",
            "WORKER_DISPATCH_FAILED",
            "DISPATCH_FAILED",
        ]
        or rows[2].get("phase") != "evidence"
        or rows[2].get("worker") != 0
        or rows[3].get("dispatched_worker_count") != 0
        or any(row.get("event") == "WORKER_DISPATCHED" for row in rows)
    ):
        raise LearnedResourceForecastPostprocessU003V1Error(
            "U002 failed evidence dispatch is not the exact zero-worker failure history"
        )


def _preanalysis_expected_counts() -> dict[str, int]:
    excluded = {
        "successor_encoder_pt",
        "successor_encoder_receipt",
        "successor_matrix_npz",
        "successor_matrix_metadata",
        "successor_pilot_result",
        "successor_verification",
        "postprocess_status",
    }
    return {
        category: count
        for category, count in EXPECTED_CATEGORY_COUNTS_V1.items()
        if category not in excluded
    }


def _validate_prerequisites(
    *,
    predecessor_protocol: dict[str, Any],
    predecessor_manifest: dict[str, Any],
    successor_protocol: dict[str, Any],
    successor_manifest: dict[str, Any],
) -> tuple[list[Path], list[Path], list[RetentionEntryV1]]:
    del predecessor_protocol, successor_protocol
    old_fixed = predecessor_manifest["fixed_paths"]
    new_fixed = successor_manifest["fixed_paths"]
    old_results = Path(old_fixed["results_root"])
    new_results = Path(new_fixed["results_root"])
    training_dirs = [old_results / f"worker-{index}" for index in range(6)]
    evidence_dirs = [new_results / f"worker-{index}" for index in range(6)]
    for root, directories, label in (
        (old_results, training_dirs, "U002 training results"),
        (new_results, evidence_dirs, "U003 evidence results"),
    ):
        if (
            not root.is_dir()
            or {path.name for path in root.iterdir()}
            != {path.name for path in directories}
            or any(not path.is_dir() for path in directories)
        ):
            raise LearnedResourceForecastPostprocessU003V1Error(
                f"{label} root is not exactly six worker directories"
            )

    entries: list[RetentionEntryV1] = []
    for index in range(6):
        old_worker = predecessor_manifest["workers"][index]
        new_worker = successor_manifest["workers"][index]
        old_dir, new_dir = training_dirs[index], evidence_dirs[index]
        old_artifacts = _predecessor_artifact_map(old_worker)
        new_artifacts = _successor_artifact_map(new_worker)
        _require_exact_directory(
            old_dir, set(old_artifacts), f"U002 worker-{index} training directory"
        )
        _require_exact_directory(
            new_dir, set(new_artifacts), f"U003 worker-{index} evidence directory"
        )
        for filename, category in old_artifacts.items():
            entries.append(
                (
                    old_dir / filename,
                    category,
                    PROVENANCE_U002_TRAINING_V1,
                    Path("predecessor-u002/training/workers")
                    / old_dir.name
                    / filename,
                )
            )
        for filename, category in new_artifacts.items():
            entries.append(
                (
                    new_dir / filename,
                    category,
                    PROVENANCE_U003_EVIDENCE_V1,
                    Path("successor-u003/evidence/workers")
                    / new_dir.name
                    / filename,
                )
            )

    old_status_root = Path(old_fixed["status_root"])
    old_log_root = Path(old_fixed["log_root"])
    new_status_root = Path(new_fixed["status_root"])
    new_log_root = Path(new_fixed["log_root"])
    old_status_names = {
        worker["policy_training_status_stream"]
        for worker in predecessor_manifest["workers"]
    }
    old_log_names = {
        f"worker-{worker['worker']}-training.log"
        for worker in predecessor_manifest["workers"]
    }
    new_status_names = {
        worker["player_evidence_status_stream"]
        for worker in successor_manifest["workers"]
    }
    new_log_names = {
        f"worker-{worker['worker']}-evidence.log"
        for worker in successor_manifest["workers"]
    }
    _require_exact_directory(old_status_root, old_status_names, "U002 training status root")
    _require_exact_directory(old_log_root, old_log_names, "U002 training log root")
    _require_exact_directory(new_status_root, new_status_names, "U003 evidence status root")
    _require_exact_directory(new_log_root, new_log_names, "U003 evidence log root")
    for index in range(6):
        old_worker = predecessor_manifest["workers"][index]
        new_worker = successor_manifest["workers"][index]
        old_status = old_status_root / old_worker["policy_training_status_stream"]
        old_log = old_log_root / f"worker-{index}-training.log"
        new_status = new_status_root / new_worker["player_evidence_status_stream"]
        new_log = new_log_root / f"worker-{index}-evidence.log"
        _validate_worker_status(
            old_status,
            phase="training",
            worker_index=index,
            jobs=old_worker["policy_training_jobs"],
        )
        _validate_worker_log(
            old_log,
            phase="training",
            worker_index=index,
            expected_count=24,
            results_root=training_dirs[index],
        )
        _validate_worker_status(
            new_status,
            phase="evidence",
            worker_index=index,
            jobs=new_worker["player_evidence_jobs"],
        )
        _validate_worker_log(
            new_log,
            phase="evidence",
            worker_index=index,
            expected_count=72,
            results_root=evidence_dirs[index],
        )
        entries.extend(
            (
                (
                    old_status,
                    "predecessor_training_worker_status",
                    PROVENANCE_U002_TRAINING_V1,
                    Path("predecessor-u002/training/status") / old_status.name,
                ),
                (
                    old_log,
                    "predecessor_training_worker_log",
                    PROVENANCE_U002_TRAINING_V1,
                    Path("predecessor-u002/training/logs") / old_log.name,
                ),
                (
                    new_status,
                    "successor_evidence_worker_status",
                    PROVENANCE_U003_EVIDENCE_V1,
                    Path("successor-u003/evidence/status") / new_status.name,
                ),
                (
                    new_log,
                    "successor_evidence_worker_log",
                    PROVENANCE_U003_EVIDENCE_V1,
                    Path("successor-u003/evidence/logs") / new_log.name,
                ),
            )
        )

    old_dispatch = Path(old_fixed["training_dispatch_status"])
    new_dispatch = Path(new_fixed["evidence_dispatch_status"])
    failed_dispatch = Path(new_fixed["ineligible_predecessor_evidence_dispatch_status"])
    _validate_dispatch_status(
        old_dispatch,
        phase="training",
        manifest=predecessor_manifest,
        fixed=old_fixed,
        successor=False,
    )
    _validate_dispatch_status(
        new_dispatch,
        phase="evidence",
        manifest=successor_manifest,
        fixed=new_fixed,
        successor=True,
    )
    _validate_ineligible_failed_dispatch(failed_dispatch)
    entries.extend(
        (
            (
                old_dispatch,
                "predecessor_training_dispatch_status",
                PROVENANCE_U002_TRAINING_V1,
                Path("predecessor-u002/training/dispatch") / old_dispatch.name,
            ),
            (
                failed_dispatch,
                "ineligible_predecessor_failed_evidence_dispatch",
                PROVENANCE_FAILED_U002_EVIDENCE_V1,
                Path("predecessor-u002/failure-history") / failed_dispatch.name,
            ),
            (
                new_dispatch,
                "successor_evidence_dispatch_status",
                PROVENANCE_U003_EVIDENCE_V1,
                Path("successor-u003/evidence/dispatch") / new_dispatch.name,
            ),
        )
    )

    authority = (
        (
            Path(new_fixed["predecessor_protocol"]),
            "predecessor_protocol",
            PROVENANCE_U002_TRAINING_V1,
            Path("predecessor-u002/authority/protocol.json"),
        ),
        (
            Path(new_fixed["predecessor_manifest"]),
            "predecessor_manifest",
            PROVENANCE_U002_TRAINING_V1,
            Path("predecessor-u002/authority/launch-manifest.json"),
        ),
        (
            Path(new_fixed["protocol"]),
            "successor_protocol",
            PROVENANCE_U003_EVIDENCE_V1,
            Path("successor-u003/authority/protocol.json"),
        ),
        (
            Path(new_fixed["manifest"]),
            "successor_manifest",
            PROVENANCE_U003_EVIDENCE_V1,
            Path("successor-u003/authority/launch-manifest.json"),
        ),
        (
            Path(new_fixed["history_scan_receipt"]),
            "successor_history_scan_receipt",
            PROVENANCE_U003_EVIDENCE_V1,
            Path("successor-u003/authority/history-scan-receipt.json"),
        ),
        (
            Path(new_fixed["gather_transport_marker"]),
            "gather_transport_marker",
            PROVENANCE_GATHER_V1,
            Path("gather/gather-transport-marker.json"),
        ),
        (
            Path(new_fixed["gather_receipt"]),
            "gather_receipt",
            PROVENANCE_GATHER_V1,
            Path("gather/gather-receipt.json"),
        ),
    )
    for entry in authority:
        if not entry[0].is_file():
            raise LearnedResourceForecastPostprocessU003V1Error(
                f"retained dual-authority input is missing: {entry[0]}"
            )
        entries.append(entry)

    category_counts: dict[str, int] = {}
    for _path, category, _provenance, _relative in entries:
        category_counts[category] = category_counts.get(category, 0) + 1
    if category_counts != _preanalysis_expected_counts():
        raise LearnedResourceForecastPostprocessU003V1Error(
            "dual-authority preanalysis category counts do not close exactly"
        )
    return training_dirs, evidence_dirs, entries


def _analysis_entries(analysis_root: Path) -> list[RetentionEntryV1]:
    categories = {
        "aligned-resource-forecast.encoder.pt": "successor_encoder_pt",
        "player-shuffled-resource-forecast.encoder.pt": "successor_encoder_pt",
        "aligned-resource-forecast.receipt.json": "successor_encoder_receipt",
        "player-shuffled-resource-forecast.receipt.json": (
            "successor_encoder_receipt"
        ),
        "probe-representation-matrices.npz": "successor_matrix_npz",
        "probe-representation-matrices.metadata.json": (
            "successor_matrix_metadata"
        ),
        "pilot-result.json": "successor_pilot_result",
        "independent-verification.json": "successor_verification",
    }
    _require_exact_directory(analysis_root, set(categories), "U003 analysis output root")
    return [
        (
            analysis_root / filename,
            category,
            PROVENANCE_ANALYSIS_V1,
            Path("successor-u003/analysis") / filename,
        )
        for filename, category in categories.items()
    ]


def _copy_retained(
    *,
    entries: list[RetentionEntryV1],
    retained_root: Path,
    predecessor_protocol: dict[str, Any],
    successor_protocol: dict[str, Any],
) -> dict[str, Any]:
    if retained_root.exists():
        raise LearnedResourceForecastPostprocessU003V1Error(
            "U003 retained root already exists; retention identity is consumed"
        )
    retained_root.mkdir(parents=False)
    inventory_rows: list[dict[str, Any]] = []
    category_counts: dict[str, int] = {}
    provenance_counts: dict[str, int] = {}
    for source, category, provenance, relative in entries:
        if not source.is_file():
            raise LearnedResourceForecastPostprocessU003V1Error(
                f"U003 retention source disappeared: {source}"
            )
        target = retained_root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            raise LearnedResourceForecastPostprocessU003V1Error(
                "U003 retention destination collision changed the exact inventory"
            )
        shutil.copy2(source, target)
        inventory_rows.append(
            {
                "category": category,
                "provenance": provenance,
                "source_path": str(source),
                "retained_relative_path": relative.as_posix(),
                "size_bytes": target.stat().st_size,
            }
        )
        category_counts[category] = category_counts.get(category, 0) + 1
        provenance_counts[provenance] = provenance_counts.get(provenance, 0) + 1
    if category_counts != EXPECTED_CATEGORY_COUNTS_V1:
        raise LearnedResourceForecastPostprocessU003V1Error(
            "U003 retention category counts differ from the registered inventory"
        )
    if provenance_counts != EXPECTED_PROVENANCE_COUNTS_V1:
        raise LearnedResourceForecastPostprocessU003V1Error(
            "U003 retention provenance counts differ from the dual-authority boundary"
        )
    inventory = {
        "schema": SCHEMA_V1,
        "predecessor_protocol_id": predecessor_protocol["protocol_id"],
        "predecessor_source_commit": predecessor_protocol["source_commit"],
        "predecessor_pilot_execution_identity": predecessor_protocol[
            "pilot_execution_identity"
        ],
        "successor_protocol_id": successor_protocol["protocol_id"],
        "successor_source_commit": successor_protocol["source_commit"],
        "successor_pilot_execution_identity": successor_protocol[
            "pilot_execution_identity"
        ],
        "authority_mode": "READ_ONLY_U002_TRAINING_PLUS_FRESH_U003_EVIDENCE",
        "failed_u002_evidence_dispatch_used": False,
        "predecessor_training_and_successor_evidence_retained_separately": True,
        "retention_complete": True,
        "category_counts": category_counts,
        "provenance_counts": provenance_counts,
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
        raise LearnedResourceForecastPostprocessU003V1Error(
            "U003 retained tree contains a missing or foreign physical file"
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
    predecessor_protocol_path = require_path_outside_repository_v1(
        repository=REPOSITORY,
        path=args.predecessor_protocol,
        label="ratified U002 predecessor protocol",
    )
    predecessor_manifest_path = require_path_outside_repository_v1(
        repository=REPOSITORY,
        path=args.predecessor_manifest,
        label="U002 predecessor launch manifest",
    )
    successor_protocol_path = require_path_outside_repository_v1(
        repository=REPOSITORY,
        path=args.protocol,
        label="ratified U003 successor protocol",
    )
    successor_manifest_path = require_path_outside_repository_v1(
        repository=REPOSITORY,
        path=args.manifest,
        label="U003 successor launch manifest",
    )
    history_path = require_path_outside_repository_v1(
        repository=REPOSITORY,
        path=args.history_scan_receipt,
        label="U003 history-scan receipt",
    )
    gather_path = require_path_outside_repository_v1(
        repository=REPOSITORY,
        path=args.gather_receipt,
        label="U003 dual-authority gather receipt",
    )
    predecessor_protocol = validate_ratified_learned_resource_forecast_protocol_v1(
        _read_object(predecessor_protocol_path, "ratified U002 predecessor protocol")
    )
    successor_protocol = (
        validate_ratified_learned_resource_forecast_evidence_successor_protocol_v1(
            _read_object(successor_protocol_path, "ratified U003 successor protocol")
        )
    )
    predecessor_manifest = _read_object(
        predecessor_manifest_path, "U002 predecessor launch manifest"
    )
    successor_manifest = _read_object(
        successor_manifest_path, "U003 successor launch manifest"
    )
    if predecessor_manifest != _load_predecessor_prepare_module().build_launch_manifest_v1(
        predecessor_protocol
    ):
        raise LearnedResourceForecastPostprocessU003V1Error(
            "U002 predecessor manifest does not replay from its protocol"
        )
    if successor_manifest != _load_successor_prepare_module().build_launch_manifest_v1(
        successor_protocol
    ):
        raise LearnedResourceForecastPostprocessU003V1Error(
            "U003 successor manifest does not replay from its protocol"
        )
    fixed = successor_manifest["fixed_paths"]
    analysis_root = Path(fixed["analysis_root"]).resolve()
    retained_root = Path(fixed["retained_root"]).resolve()
    status_path = Path(fixed["postprocess_status"]).resolve()
    source_commit = bound_clean_source_commit_v1(REPOSITORY)
    parent = successor_protocol["predecessor_training_authority"]
    if (
        source_commit != successor_protocol["source_commit"]
        or REPOSITORY.resolve() != Path(fixed["source_checkout"]).resolve()
        or predecessor_protocol_path != Path(fixed["predecessor_protocol"]).resolve()
        or predecessor_manifest_path != Path(fixed["predecessor_manifest"]).resolve()
        or successor_protocol_path != Path(fixed["protocol"]).resolve()
        or successor_manifest_path != Path(fixed["manifest"]).resolve()
        or history_path != Path(fixed["history_scan_receipt"]).resolve()
        or gather_path != Path(fixed["gather_receipt"]).resolve()
        or predecessor_protocol["protocol_id"] != parent["protocol_id"]
        or predecessor_protocol["source_commit"] != parent["source_commit"]
        or predecessor_protocol["pilot_execution_identity"]
        != parent["pilot_execution_identity"]
        or socket.gethostname()
        != successor_manifest["central_analysis"]["expected_hostname"]
        or args.analysis_device != successor_manifest["central_analysis"]["device"]
        or args.verifier_device != successor_manifest["central_analysis"]["device"]
    ):
        raise LearnedResourceForecastPostprocessU003V1Error(
            "U003 postprocess source, authority, paths, host, or devices changed"
        )
    history = _load_history_scan_module()
    history.validate_history_scan_receipt_v1(
        _read_object(history_path, "U003 history-scan receipt"),
        successor_protocol,
        successor_manifest,
    )
    gather = _load_gather_module()
    gather.validate_gather_receipt_v1(
        _read_object(gather_path, "U003 gather receipt"),
        predecessor_protocol,
        successor_protocol,
        predecessor_manifest,
        successor_manifest,
    )
    if analysis_root.exists() or retained_root.exists() or status_path.exists():
        raise LearnedResourceForecastPostprocessU003V1Error(
            "U003 analysis, retained, or status target already exists; attempt is consumed"
        )

    run_analysis = analysis_runner or _default_analysis_runner
    run_verifier = verifier_runner or _default_verifier_runner
    copy_retained = retention_copier or _copy_retained
    validate_runtime = runtime_validator or _default_runtime_validator
    validate_runtime(
        predecessor_protocol_path,
        predecessor_manifest_path,
        successor_protocol_path,
        successor_manifest_path,
        args.analysis_device,
    )
    training_dirs, evidence_dirs, retention_entries = _validate_prerequisites(
        predecessor_protocol=predecessor_protocol,
        predecessor_manifest=predecessor_manifest,
        successor_protocol=successor_protocol,
        successor_manifest=successor_manifest,
    )
    old_fixed = predecessor_manifest["fixed_paths"]
    with _ExclusiveStatusStreamV1(status_path) as status:
        status.emit(
            {
                "event": "POSTPROCESS_STARTED",
                "predecessor_protocol_id": predecessor_protocol["protocol_id"],
                "successor_protocol_id": successor_protocol["protocol_id"],
                "source_commit": source_commit,
                "host": socket.gethostname(),
                "authority_mode": (
                    "READ_ONLY_U002_TRAINING_PLUS_FRESH_U003_EVIDENCE"
                ),
            }
        )
        try:
            status.emit(
                {
                    "event": "PREREQUISITES_COMPLETED",
                    "predecessor_training_worker_directory_count": 6,
                    "predecessor_training_job_count": 144,
                    "predecessor_model_snapshot_count": 432,
                    "successor_evidence_worker_directory_count": 6,
                    "successor_evidence_job_count": 432,
                    "failed_u002_evidence_dispatch_used": False,
                }
            )
            analysis_root.mkdir(parents=False)
            common = {
                "predecessor_protocol": predecessor_protocol_path,
                "predecessor_manifest": predecessor_manifest_path,
                "protocol": successor_protocol_path,
                "manifest": successor_manifest_path,
                "device": args.analysis_device,
            }
            stages = [
                (
                    "FIT_ENCODERS",
                    SimpleNamespace(
                        operation="fit-encoders",
                        trajectory_dir=evidence_dirs,
                        output_dir=analysis_root,
                        **common,
                    ),
                ),
                (
                    "ENCODE_PROBES",
                    SimpleNamespace(
                        operation="encode-probes",
                        probe_dir=evidence_dirs,
                        aligned_encoder=(
                            analysis_root / "aligned-resource-forecast.encoder.pt"
                        ),
                        shuffled_encoder=(
                            analysis_root
                            / "player-shuffled-resource-forecast.encoder.pt"
                        ),
                        output_dir=analysis_root,
                        **common,
                    ),
                ),
                (
                    "EVALUATE",
                    SimpleNamespace(
                        operation="evaluate",
                        predecessor_status_dir=[Path(old_fixed["status_root"])],
                        status_dir=[Path(fixed["status_root"])],
                        predecessor_training_result_dir=training_dirs,
                        worker_result_dir=evidence_dirs,
                        matrix=analysis_root / "probe-representation-matrices.npz",
                        matrix_metadata=(
                            analysis_root
                            / "probe-representation-matrices.metadata.json"
                        ),
                        encoder_receipt_dir=analysis_root,
                        label_dir=evidence_dirs,
                        output=analysis_root / "pilot-result.json",
                        **common,
                    ),
                ),
            ]
            for stage_name, stage_args in stages:
                status.emit({"event": "STAGE_STARTED", "stage": stage_name})
                summary = run_analysis(stage_args)
                if summary.get("success") is not True:
                    raise LearnedResourceForecastPostprocessU003V1Error(
                        f"U003 analysis stage returned no exact success: {stage_name}"
                    )
                status.emit({"event": "STAGE_COMPLETED", "stage": stage_name})
            status.emit(
                {"event": "STAGE_STARTED", "stage": "INDEPENDENT_VERIFIER"}
            )
            verification_summary = run_verifier(
                SimpleNamespace(
                    predecessor_protocol=predecessor_protocol_path,
                    predecessor_manifest=predecessor_manifest_path,
                    protocol=successor_protocol_path,
                    manifest=successor_manifest_path,
                    predecessor_status_dir=[Path(old_fixed["status_root"])],
                    status_dir=[Path(fixed["status_root"])],
                    trajectory_dir=evidence_dirs,
                    probe_dir=evidence_dirs,
                    label_dir=evidence_dirs,
                    encoder_dir=analysis_root,
                    predecessor_training_result_dir=training_dirs,
                    worker_result_dir=evidence_dirs,
                    matrix=analysis_root / "probe-representation-matrices.npz",
                    matrix_metadata=(
                        analysis_root / "probe-representation-matrices.metadata.json"
                    ),
                    result=analysis_root / "pilot-result.json",
                    output=analysis_root / "independent-verification.json",
                    device=args.verifier_device,
                )
            )
            if verification_summary.get("success") is not True:
                raise LearnedResourceForecastPostprocessU003V1Error(
                    "U003 independent verifier returned no exact success"
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
                    "failed_u002_evidence_dispatch_used": False,
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
            PROVENANCE_POSTPROCESS_V1,
            Path("successor-u003/status") / status_path.name,
        )
    )
    inventory = copy_retained(
        entries=retention_entries,
        retained_root=retained_root,
        predecessor_protocol=predecessor_protocol,
        successor_protocol=successor_protocol,
    )
    result = _read_object(analysis_root / "pilot-result.json", "U003 pilot result")
    verification = _read_object(
        analysis_root / "independent-verification.json",
        "U003 independent verification",
    )
    return {
        "success": True,
        "predecessor_protocol_id": predecessor_protocol["protocol_id"],
        "successor_protocol_id": successor_protocol["protocol_id"],
        "analysis_root": str(analysis_root),
        "retained_root": str(retained_root),
        "postprocess_status": str(status_path),
        "authority_mode": "READ_ONLY_U002_TRAINING_PLUS_FRESH_U003_EVIDENCE",
        "failed_u002_evidence_dispatch_used": False,
        "retained_artifact_count_excluding_inventory": inventory[
            "retained_artifact_count_excluding_inventory"
        ],
        "physical_file_count_including_inventory": inventory[
            "physical_file_count_including_inventory"
        ],
        "PROVISIONAL_DESIGN_SIGNAL_GATE": result.get(
            "PROVISIONAL_DESIGN_SIGNAL_GATE"
        ),
        "independent_verification": verification.get("valid"),
    }


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--predecessor-protocol", type=Path, required=True)
    parser.add_argument("--predecessor-manifest", type=Path, required=True)
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
        LearnedResourceForecastPostprocessU003V1Error,
        LearnedResourceForecastEvidenceSuccessorProtocolV1Error,
        LearnedResourceForecastProtocolV1Error,
        ScienceExecutionIOV1Error,
    ) as error:
        raise SystemExit(str(error)) from error
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
