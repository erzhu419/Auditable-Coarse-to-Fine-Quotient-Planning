"""Join one exact hybrid manifest to retained status and job artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, NoReturn

from acfqp.science.latent_resource_hybrid_confirmatory_protocol_v1 import (
    HYBRID_CONFIRMATORY_ARMS_V1,
    HYBRID_CONFIRMATORY_TRAINING_SEEDS_V1,
    LatentResourceHybridConfirmatoryProtocolV1Error,
    registered_hybrid_confirmatory_device_v1,
    validate_ratified_hybrid_confirmatory_protocol_v1,
)


HYBRID_CONFIRMATORY_MANIFEST_SCHEMA_V1 = (
    "acfqp.science.latent_resource_hybrid_confirmatory_launch_manifest.v1"
)


class HybridConfirmatoryEvaluatorV1Error(ValueError):
    """The manifest, status closure, or artifact join is incomplete."""


def _fail(message: str) -> NoReturn:
    raise HybridConfirmatoryEvaluatorV1Error(message)


def _object_v1(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise HybridConfirmatoryEvaluatorV1Error(
            f"cannot read one JSON object from {path}"
        ) from error
    if type(value) is not dict:
        _fail(f"{path} must contain one JSON object")
    return value


def _status_events_v1(path: Path) -> list[dict[str, Any]]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
        rows = [json.loads(line) for line in lines]
    except (OSError, json.JSONDecodeError) as error:
        raise HybridConfirmatoryEvaluatorV1Error(
            f"cannot read worker status stream {path}"
        ) from error
    if not rows or any(type(row) is not dict for row in rows):
        _fail(f"{path} contains no complete object status stream")
    return rows


def load_evidence_bound_hybrid_confirmatory_matrix_v1(
    *,
    protocol: Mapping[str, Any],
    manifest: Mapping[str, Any],
    results_root: Path,
) -> list[dict[str, Any]]:
    """Load only the exact 30 jobs closed by status, JSON, model, and log."""

    try:
        validated = validate_ratified_hybrid_confirmatory_protocol_v1(protocol)
    except LatentResourceHybridConfirmatoryProtocolV1Error as error:
        raise HybridConfirmatoryEvaluatorV1Error(str(error)) from error
    if type(manifest) is not dict:
        _fail("hybrid confirmatory manifest must be a plain object")
    jobs = manifest.get("jobs")
    worker_count = manifest.get("worker_count")
    if (
        manifest.get("schema") != HYBRID_CONFIRMATORY_MANIFEST_SCHEMA_V1
        or manifest.get("protocol_id") != validated["protocol_id"]
        or manifest.get("source_commit") != validated["source_commit"]
        or manifest.get("job_count") != 30
        or type(jobs) is not list
        or len(jobs) != 30
        or worker_count != 2
    ):
        _fail("manifest identity or fixed 30-job shape changed")
    if any(type(job) is not dict for job in jobs):
        _fail("manifest job row must be a plain object")
    ordered = sorted(jobs, key=lambda job: job.get("job_ordinal", -1))
    if [job.get("job_ordinal") for job in ordered] != list(range(30)):
        _fail("manifest job ordinals changed")
    expected_identities = {
        (arm, seed)
        for arm in HYBRID_CONFIRMATORY_ARMS_V1
        for seed in HYBRID_CONFIRMATORY_TRAINING_SEEDS_V1
    }
    identities: set[tuple[str, int]] = set()
    execution_ids: set[str] = set()
    jobs_by_worker: dict[int, set[str]] = {
        worker: set() for worker in range(worker_count)
    }
    for job in ordered:
        identity = (job.get("arm"), job.get("seed"))
        execution_id = job.get("execution_id")
        worker = job.get("worker")
        device = job.get("device")
        if (
            identity not in expected_identities
            or identity in identities
            or type(execution_id) is not str
            or not execution_id
            or execution_id in execution_ids
            or type(worker) is not int
            or worker not in jobs_by_worker
            or device != registered_hybrid_confirmatory_device_v1(job.get("seed"))
            or worker != int(device.split(":", 1)[1])
        ):
            _fail("manifest contains a foreign or duplicate job identity")
        identities.add(identity)
        execution_ids.add(execution_id)
        jobs_by_worker[worker].add(execution_id)
    if identities != expected_identities or any(
        not worker_jobs for worker_jobs in jobs_by_worker.values()
    ):
        _fail("manifest does not cover the exact matrix and workers")

    completed_ids: set[str] = set()
    for worker, expected_worker_ids in jobs_by_worker.items():
        rows = _status_events_v1(results_root / f"worker-{worker}-status.jsonl")
        if any(row.get("event") == "JOB_FAILED" for row in rows):
            _fail(f"worker {worker} retained a failed confirmatory job")
        if sum(row.get("event") == "WORKER_COMPLETED" for row in rows) != 1:
            _fail(f"worker {worker} has not completed exactly once")
        worker_completed: set[str] = set()
        for row in rows:
            if row.get("event") != "JOB_COMPLETED":
                continue
            execution_id = row.get("execution_id")
            if (
                type(execution_id) is not str
                or execution_id in completed_ids
                or execution_id in worker_completed
            ):
                _fail("completed execution identities are invalid")
            worker_completed.add(execution_id)
        if worker_completed != expected_worker_ids:
            _fail(f"worker {worker} status does not close its manifest jobs")
        completed_ids.update(worker_completed)
    if completed_ids != execution_ids:
        _fail("worker statuses do not close the exact manifest")

    artifacts: list[dict[str, Any]] = []
    for job in ordered:
        stem = f"{job['arm'].lower()}-seed-{job['seed']}"
        result_path = results_root / "artifacts" / f"{stem}.json"
        model_path = results_root / "artifacts" / f"{stem}.pt"
        log_path = results_root / "logs" / f"{stem}.log"
        if not (
            result_path.is_file() and model_path.is_file() and log_path.is_file()
        ):
            _fail(f"completed job is missing JSON, model, or log: {stem}")
        artifact = _object_v1(result_path)
        context = artifact.get("execution_context")
        if (
            artifact.get("protocol_id") != validated["protocol_id"]
            or artifact.get("arm") != job["arm"]
            or artifact.get("seed") != job["seed"]
            or artifact.get("device") != job["device"]
            or type(context) is not dict
            or context.get("execution_id") != job["execution_id"]
            or context.get("source_commit") != validated["source_commit"]
        ):
            _fail(f"artifact identity differs from manifest: {stem}")
        artifacts.append(artifact)
    return artifacts


__all__ = (
    "HYBRID_CONFIRMATORY_MANIFEST_SCHEMA_V1",
    "HybridConfirmatoryEvaluatorV1Error",
    "load_evidence_bound_hybrid_confirmatory_matrix_v1",
)
