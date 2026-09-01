#!/usr/bin/env python3
"""Run one U003 evidence worker against read-only U002 policy snapshots."""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
import sys
from typing import Any, Callable

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
from acfqp.science.learned_resource_forecast_evidence_successor_protocol_v1 import (
    U002_PROTOCOL_ID_V1,
    U002_SOURCE_COMMIT_V1,
    LearnedResourceForecastEvidenceSuccessorProtocolV1Error,
    validate_ratified_learned_resource_forecast_evidence_successor_protocol_v1,
)
from acfqp.science.learned_resource_forecast_protocol_v1 import (
    LearnedResourceForecastProtocolV1Error,
    validate_ratified_learned_resource_forecast_protocol_v1,
)


REPOSITORY = Path(__file__).resolve().parents[1]
WORKER_COUNT_V1 = 6
EVIDENCE_JOBS_PER_WORKER_V1 = 72
JobRunnerV1 = Callable[[SimpleNamespace], dict[str, Any]]


class LearnedResourceForecastEvidenceSuccessorWorkerV1Error(RuntimeError):
    """A U003 worker, U002 prerequisite, or fresh artifact is ineligible."""


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--worker", type=int, choices=range(6), required=True)
    parser.add_argument("--phase", choices=("evidence",), default="evidence")
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--predecessor-protocol", type=Path, required=True)
    parser.add_argument("--predecessor-manifest", type=Path, required=True)
    parser.add_argument("--predecessor-results-root", type=Path, required=True)
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
        raise LearnedResourceForecastEvidenceSuccessorWorkerV1Error(
            f"cannot read {label}: {path}"
        ) from error
    if type(value) is not dict:
        raise LearnedResourceForecastEvidenceSuccessorWorkerV1Error(
            f"{label} must contain one JSON object"
        )
    return value


def _load_script(name: str, filename: str):
    path = REPOSITORY / "scripts" / filename
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise LearnedResourceForecastEvidenceSuccessorWorkerV1Error(
            f"cannot load worker dependency: {path}"
        )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _prepare_module():
    return _load_script(
        "acfqp_u003_prepare_for_worker",
        "prepare_learned_resource_forecast_evidence_successor_u003.py",
    )


def _u002_prepare_module():
    return _load_script(
        "acfqp_u002_prepare_for_u003_worker",
        "prepare_learned_resource_forecast_campaign_u002.py",
    )


def _u002_worker_module():
    return _load_script(
        "acfqp_u002_worker_helpers_for_u003",
        "run_learned_resource_forecast_worker_u002.py",
    )


def _u002_postprocess_module():
    return _load_script(
        "acfqp_u002_postprocess_helpers_for_u003",
        "postprocess_retain_learned_resource_forecast_u002.py",
    )


def _evidence_targets(job: dict[str, Any], root: Path) -> tuple[Path, ...]:
    names = [job["label_filename"], job["probe_filename"]]
    if job["split"] == "TRAIN":
        names.extend(
            [job["trajectory_metadata_filename"], job["trajectory_array_filename"]]
        )
    if any(type(name) is not str or not name for name in names):
        raise LearnedResourceForecastEvidenceSuccessorWorkerV1Error(
            "U003 evidence target roster changed"
        )
    return tuple(root / name for name in names)


def _expected_evidence_names(worker: dict[str, Any]) -> set[str]:
    names = {
        path.name
        for job in worker["player_evidence_jobs"]
        for path in _evidence_targets(job, Path("."))
    }
    expected = 252 if worker["train_seed_count"] == 6 else 234
    if len(names) != expected:
        raise LearnedResourceForecastEvidenceSuccessorWorkerV1Error(
            "worker evidence artifact roster changed"
        )
    return names


def _validate_parent_authority(
    *,
    protocol: dict[str, Any],
    manifest: dict[str, Any],
    predecessor_protocol: dict[str, Any],
    predecessor_manifest: dict[str, Any],
    worker: dict[str, Any],
    predecessor_root: Path,
) -> None:
    parent = protocol["predecessor_training_authority"]
    if (
        predecessor_protocol["protocol_id"] != U002_PROTOCOL_ID_V1
        or predecessor_protocol["source_commit"] != U002_SOURCE_COMMIT_V1
        or parent["protocol_id"] != predecessor_protocol["protocol_id"]
        or parent["source_commit"] != predecessor_protocol["source_commit"]
        or predecessor_manifest
        != _u002_prepare_module().build_launch_manifest_v1(predecessor_protocol)
    ):
        raise LearnedResourceForecastEvidenceSuccessorWorkerV1Error(
            "U002 predecessor protocol or manifest authority changed"
        )
    parent_worker = predecessor_manifest["workers"][worker["worker"]]
    if (
        parent_worker["host_alias"] != worker["host_alias"]
        or parent_worker["expected_hostname"] != worker["expected_hostname"]
        or parent_worker["device"] != worker["device"]
        or parent_worker["seeds"] != worker["seeds"]
        or parent_worker["policy_training_jobs"]
        != [
            {key: value for key, value in job.items() if key != "provenance"}
            for job in worker["predecessor_policy_training_jobs"]
        ]
        or predecessor_root
        != Path(worker["predecessor_snapshot_root"]).resolve()
    ):
        raise LearnedResourceForecastEvidenceSuccessorWorkerV1Error(
            "U003 worker no longer uses exact U002 host/GPU/player ownership"
        )
    helpers = _u002_worker_module()
    postprocess = _u002_postprocess_module()
    postprocess._require_exact_directory(
        predecessor_root,
        helpers._training_artifact_names(parent_worker),
        "read-only U002 training worker directory",
    )
    helpers._validate_all_training_prerequisites(
        protocol=predecessor_protocol,
        worker=parent_worker,
        root=predecessor_root,
    )
    parent_status = (
        Path(manifest["fixed_paths"]["predecessor_status_root"])
        / worker["predecessor_training_status_stream"]
    )
    parent_log = (
        Path(manifest["fixed_paths"]["predecessor_log_root"])
        / worker["predecessor_training_log"]
    )
    postprocess._validate_worker_status(
        parent_status, phase="training", worker=parent_worker
    )
    postprocess._validate_worker_log(
        parent_log,
        phase="training",
        worker=parent_worker,
        results_root=predecessor_root,
    )


def _validate_evidence_artifacts(
    *,
    protocol: dict[str, Any],
    predecessor_protocol: dict[str, Any],
    worker: dict[str, Any],
    job: dict[str, Any],
    root: Path,
) -> None:
    contracts = [
        (job["label_filename"], LABEL_EVIDENCE_SCHEMA_V1),
        (job["probe_filename"], PROBE_EVIDENCE_SCHEMA_V1),
    ]
    if job["split"] == "TRAIN":
        contracts.append(
            (job["trajectory_metadata_filename"], TRAJECTORY_EVIDENCE_SCHEMA_V1)
        )
        if not (root / job["trajectory_array_filename"]).is_file():
            raise LearnedResourceForecastEvidenceSuccessorWorkerV1Error(
                "train-player U003 evidence lost trajectory array"
            )
    for filename, schema in contracts:
        document = _read_object(root / filename, "U003 evidence lane artifact")
        snapshot = document.get("policy_snapshot", {})
        if (
            document.get("schema") != schema
            or document.get("protocol_id") != protocol["protocol_id"]
            or document.get("source_commit") != protocol["source_commit"]
            or document.get("pilot_execution_identity")
            != protocol["pilot_execution_identity"]
            or document.get("player_identity", {}).get("player_key")
            != job["player_key"]
            or document.get("player_identity", {}).get("split") != job["split"]
            or document.get("execution_context", {}).get("execution_id")
            != job["execution_id"]
            or document.get("execution_context", {}).get("hostname")
            != worker["expected_hostname"]
            or document.get("execution_context", {}).get("device")
            != worker["device"]
            or snapshot.get("predecessor_protocol_id")
            != predecessor_protocol["protocol_id"]
            or snapshot.get("predecessor_source_commit")
            != predecessor_protocol["source_commit"]
            or snapshot.get("predecessor_training_execution_id")
            != job["predecessor_training_execution_id"]
            or snapshot.get("snapshot_is_read_only_predecessor_input") is not True
            or snapshot.get("snapshot_is_u003_training_artifact") is not False
            or Path(str(snapshot.get("path", ""))).resolve()
            != (Path(worker["predecessor_snapshot_root"]) / job["model_filename"]).resolve()
        ):
            raise LearnedResourceForecastEvidenceSuccessorWorkerV1Error(
                "U003 evidence artifact lost measurement or parent provenance"
            )


def _run_player_job(args: SimpleNamespace) -> dict[str, Any]:
    module = _load_script(
        "acfqp_u003_player_evidence_for_worker",
        "run_learned_resource_player_evidence_u003.py",
    )
    return module._run(args)


def _execute_jobs(
    *,
    protocol: dict[str, Any],
    predecessor_protocol: dict[str, Any],
    worker: dict[str, Any],
    protocol_path: Path,
    predecessor_protocol_path: Path,
    predecessor_root: Path,
    output_root: Path,
    status,
    runner: JobRunnerV1,
) -> int:
    helpers = _u002_worker_module()
    jobs = worker["player_evidence_jobs"]
    if len(jobs) != EVIDENCE_JOBS_PER_WORKER_V1:
        raise LearnedResourceForecastEvidenceSuccessorWorkerV1Error(
            "U003 worker no longer owns exactly 72 evidence jobs"
        )
    completed = 0
    for ordinal, job in enumerate(jobs):
        targets = _evidence_targets(job, output_root)
        status.emit(
            {
                "event": "JOB_STARTED",
                "phase": "evidence",
                "worker": worker["worker"],
                "job_ordinal": ordinal,
                "preexecution_identity_check_only": False,
                "execution_id": job["execution_id"],
                "arm": job["arm"],
                "seed": job["seed"],
                "checkpoint": job["checkpoint"],
                "player_key": job["player_key"],
                "predecessor_training_execution_id": job[
                    "predecessor_training_execution_id"
                ],
            }
        )
        arguments = SimpleNamespace(
            protocol=protocol_path,
            predecessor_protocol=predecessor_protocol_path,
            snapshot=predecessor_root / job["model_filename"],
            arm=job["arm"],
            seed=job["seed"],
            checkpoint=job["checkpoint"],
            device=worker["device"],
            output_dir=output_root,
            execution_id=job["execution_id"],
            predecessor_training_execution_id=job[
                "predecessor_training_execution_id"
            ],
        )
        try:
            summary = runner(arguments)
            if (
                type(summary) is not dict
                or summary.get("success") is not True
                or summary.get("execution_id") != job["execution_id"]
                or summary.get("predecessor_training_execution_id")
                != job["predecessor_training_execution_id"]
                or summary.get("player_key") != job["player_key"]
                or summary.get("split") != job["split"]
                or summary.get("artifact_count") != len(targets)
                or {
                    Path(path).resolve()
                    for path in summary.get("artifact_paths", {}).values()
                }
                != {path.resolve() for path in targets}
                or not all(path.is_file() for path in targets)
            ):
                raise LearnedResourceForecastEvidenceSuccessorWorkerV1Error(
                    "U003 player runner returned foreign or incomplete summary"
                )
            _validate_evidence_artifacts(
                protocol=protocol,
                predecessor_protocol=predecessor_protocol,
                worker=worker,
                job=job,
                root=output_root,
            )
        except Exception as error:
            status.emit(
                {
                    "event": "JOB_FAILED",
                    "phase": "evidence",
                    "worker": worker["worker"],
                    "job_ordinal": ordinal,
                    "execution_id": job["execution_id"],
                    "failure_kind": type(error).__name__,
                    "failure_message": str(error),
                }
            )
            raise
        finally:
            helpers._release_job_memory()
        completed += 1
        status.emit(
            {
                "event": "JOB_COMPLETED",
                "phase": "evidence",
                "worker": worker["worker"],
                "job_ordinal": ordinal,
                "completed_job_count": completed,
                "expected_job_count": EVIDENCE_JOBS_PER_WORKER_V1,
                "execution_id": job["execution_id"],
                "arm": job["arm"],
                "seed": job["seed"],
                "checkpoint": job["checkpoint"],
                "player_key": job["player_key"],
                "predecessor_training_execution_id": job[
                    "predecessor_training_execution_id"
                ],
            }
        )
    return completed


def _run(
    args: argparse.Namespace,
    *,
    evidence_job_runner: JobRunnerV1 | None = None,
) -> dict[str, Any]:
    if args.worker not in range(6) or args.phase != "evidence":
        raise LearnedResourceForecastEvidenceSuccessorWorkerV1Error(
            "U003 worker accepts only its frozen evidence phase"
        )
    paths = {
        "protocol": require_path_outside_repository_v1(
            repository=REPOSITORY, path=args.protocol, label="U003 protocol"
        ),
        "manifest": require_path_outside_repository_v1(
            repository=REPOSITORY, path=args.manifest, label="U003 manifest"
        ),
        "predecessor_protocol": require_path_outside_repository_v1(
            repository=REPOSITORY,
            path=args.predecessor_protocol,
            label="U002 predecessor protocol",
        ),
        "predecessor_manifest": require_path_outside_repository_v1(
            repository=REPOSITORY,
            path=args.predecessor_manifest,
            label="U002 predecessor manifest",
        ),
        "predecessor_root": require_path_outside_repository_v1(
            repository=REPOSITORY,
            path=args.predecessor_results_root,
            label="U002 predecessor worker results",
        ),
        "output_root": require_path_outside_repository_v1(
            repository=REPOSITORY,
            path=args.results_root,
            label="U003 worker evidence output",
        ),
        "status": require_path_outside_repository_v1(
            repository=REPOSITORY,
            path=args.status_stream,
            label="U003 worker status",
        ),
    }
    source_commit = bound_clean_source_commit_v1(REPOSITORY)
    protocol = (
        validate_ratified_learned_resource_forecast_evidence_successor_protocol_v1(
            _read_object(paths["protocol"], "U003 protocol")
        )
    )
    predecessor_protocol = validate_ratified_learned_resource_forecast_protocol_v1(
        _read_object(paths["predecessor_protocol"], "U002 predecessor protocol")
    )
    manifest = _read_object(paths["manifest"], "U003 manifest")
    predecessor_manifest = _read_object(
        paths["predecessor_manifest"], "U002 predecessor manifest"
    )
    if manifest != _prepare_module().build_launch_manifest_v1(protocol):
        raise LearnedResourceForecastEvidenceSuccessorWorkerV1Error(
            "U003 manifest does not replay from exact builder"
        )
    fixed = manifest["fixed_paths"]
    worker = manifest["workers"][args.worker]
    expected_output = Path(fixed["results_root"]) / f"worker-{args.worker}"
    expected_status = (
        Path(fixed["status_root"]) / worker["player_evidence_status_stream"]
    )
    if (
        source_commit != protocol["source_commit"]
        or manifest["source_commit"] != source_commit
        or manifest["protocol_id"] != protocol["protocol_id"]
        or Path(manifest["source_checkout"]).resolve() != REPOSITORY.resolve()
        or paths["protocol"] != Path(fixed["protocol"]).resolve()
        or paths["manifest"] != Path(fixed["manifest"]).resolve()
        or paths["predecessor_protocol"]
        != Path(fixed["predecessor_protocol"]).resolve()
        or paths["predecessor_manifest"]
        != Path(fixed["predecessor_manifest"]).resolve()
        or paths["predecessor_root"]
        != Path(worker["predecessor_snapshot_root"]).resolve()
        or paths["output_root"] != expected_output.resolve()
        or paths["status"] != expected_status.resolve()
        or args.device != worker["device"]
    ):
        raise LearnedResourceForecastEvidenceSuccessorWorkerV1Error(
            "U003 worker source, parent input, or successor output binding changed"
        )
    _validate_parent_authority(
        protocol=protocol,
        manifest=manifest,
        predecessor_protocol=predecessor_protocol,
        predecessor_manifest=predecessor_manifest,
        worker=worker,
        predecessor_root=paths["predecessor_root"],
    )
    helpers = _u002_worker_module()
    if args.global_preflight_only:
        if args.preflight_only:
            raise LearnedResourceForecastEvidenceSuccessorWorkerV1Error(
                "preflight modes are mutually exclusive"
            )
        helpers._require_python_implementation_v1(manifest["required_runtime"])
        context = helpers._actual_runtime_context(args.device)
        helpers._validate_runtime_binding(
            worker=worker,
            required_runtime=manifest["required_runtime"],
            source_checkout=manifest["source_checkout"],
            source_pythonpath=manifest["source_pythonpath"],
            requested_device=args.device,
            context=context,
        )
        optimizer_smoke = helpers._optimizer_smoke_v1()
        if any(
            Path(fixed[key]).exists()
            for key in ("results_root", "status_root", "log_root")
        ):
            raise LearnedResourceForecastEvidenceSuccessorWorkerV1Error(
                "U003 global preflight requires all successor roots absent"
            )
        return {
            "success": True,
            "global_preflight_only": True,
            "phase": "evidence",
            "worker": args.worker,
            "source_commit": source_commit,
            "protocol_id": protocol["protocol_id"],
            "predecessor_protocol_id": predecessor_protocol["protocol_id"],
            "parent_training_closure": True,
            "optimizer_smoke": optimizer_smoke,
            "filesystem_mutation": False,
        }
    if not paths["output_root"].is_dir() or any(paths["output_root"].iterdir()):
        raise LearnedResourceForecastEvidenceSuccessorWorkerV1Error(
            "U003 launcher did not provide one exactly empty worker output directory"
        )
    if paths["status"].exists():
        raise LearnedResourceForecastEvidenceSuccessorWorkerV1Error(
            "U003 status already exists; phase identity is consumed"
        )
    context = helpers._actual_runtime_context(args.device)
    helpers._validate_runtime_binding(
        worker=worker,
        required_runtime=manifest["required_runtime"],
        source_checkout=manifest["source_checkout"],
        source_pythonpath=manifest["source_pythonpath"],
        requested_device=args.device,
        context=context,
    )
    if args.preflight_only:
        return {
            "success": True,
            "preflight_only": True,
            "phase": "evidence",
            "worker": args.worker,
            "source_commit": source_commit,
            "protocol_id": protocol["protocol_id"],
            "predecessor_protocol_id": predecessor_protocol["protocol_id"],
            "predecessor_results_root": str(paths["predecessor_root"]),
            "results_root": str(paths["output_root"]),
            "status_stream": str(paths["status"]),
        }
    runner = evidence_job_runner or _run_player_job
    with helpers._ExclusiveStatusStreamV1(paths["status"]) as status:
        status.emit(
            {
                "event": "WORKER_STARTED",
                "phase": "evidence",
                "worker": args.worker,
                "host_alias": worker["host_alias"],
                "expected_hostname": worker["expected_hostname"],
                "device": args.device,
                "source_commit": source_commit,
                "protocol_id": protocol["protocol_id"],
                "predecessor_protocol_id": predecessor_protocol["protocol_id"],
                "parent_snapshot_root": str(paths["predecessor_root"]),
                "successor_evidence_output_root": str(paths["output_root"]),
            }
        )
        try:
            completed = _execute_jobs(
                protocol=protocol,
                predecessor_protocol=predecessor_protocol,
                worker=worker,
                protocol_path=paths["protocol"],
                predecessor_protocol_path=paths["predecessor_protocol"],
                predecessor_root=paths["predecessor_root"],
                output_root=paths["output_root"],
                status=status,
                runner=runner,
            )
        except Exception as error:
            status.emit(
                {
                    "event": "WORKER_FAILED",
                    "phase": "evidence",
                    "worker": args.worker,
                    "failure_kind": type(error).__name__,
                    "failure_message": str(error),
                }
            )
            raise
        status.emit(
            {
                "event": "WORKER_COMPLETED",
                "phase": "evidence",
                "worker": args.worker,
                "completed_job_count": completed,
                "runtime_context": context,
            }
        )
    return {
        "success": True,
        "phase": "evidence",
        "worker": args.worker,
        "completed_job_count": completed,
        "source_commit": source_commit,
        "protocol_id": protocol["protocol_id"],
        "predecessor_protocol_id": predecessor_protocol["protocol_id"],
        "predecessor_results_root": str(paths["predecessor_root"]),
        "results_root": str(paths["output_root"]),
        "status_stream": str(paths["status"]),
    }


def main() -> int:
    try:
        summary = _run(_arguments())
    except (
        LearnedResourceForecastEvidenceSuccessorProtocolV1Error,
        LearnedResourceForecastEvidenceSuccessorWorkerV1Error,
        LearnedResourceForecastProtocolV1Error,
        ScienceExecutionIOV1Error,
    ) as error:
        raise SystemExit(str(error)) from error
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
