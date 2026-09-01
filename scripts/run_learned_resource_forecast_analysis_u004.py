#!/usr/bin/env python3
"""Run the U004 analysis with separate U002-training and U004-evidence authority.

The numerical analysis and the irreversible lane ordering are the frozen U002
implementation.  This entry point changes only provenance: policy training is
validated against the completed U002 campaign, while every trajectory, probe,
label, encoder, matrix, result, and status event belongs to U004.
"""

from __future__ import annotations

import os

os.environ["CUBLAS_WORKSPACE_CONFIG"] = ":4096:8"

import argparse
from collections.abc import Mapping, Sequence
import importlib.util
import json
from pathlib import Path
import sys
from typing import Any, NoReturn

from acfqp.science.execution_io_v1 import ScienceExecutionIOV1Error
from acfqp.science.learned_resource_forecast_evidence_successor_protocol_v1 import (
    U002_EXECUTION_IDENTITY_V1,
    U002_PROTOCOL_ID_V1,
    U002_SOURCE_COMMIT_V1,
    LearnedResourceForecastEvidenceSuccessorProtocolV1Error,
    validate_ratified_learned_resource_forecast_evidence_successor_protocol_v1,
)
from acfqp.science.learned_resource_forecast_protocol_v1 import (
    EXPECTED_MODEL_SNAPSHOT_COUNT_V1,
    EXPECTED_PLAYER_COUNT_V1,
    EXPECTED_TRAINING_JOB_COUNT_V1,
    LEARNED_RESOURCE_FORECAST_ARMS_V1,
    LEARNED_RESOURCE_FORECAST_CHECKPOINTS_V1,
    LEARNED_RESOURCE_FORECAST_TRAINING_SEEDS_V1,
    LearnedResourceForecastProtocolV1Error,
    player_key_v1,
    validate_ratified_learned_resource_forecast_protocol_v1,
)


REPOSITORY = Path(__file__).resolve().parents[1]
SUCCESSOR_MANIFEST_SCHEMA_V1 = (
    "acfqp.science.learned_resource_forecast_2048_evidence_successor_manifest.v1"
)


class LearnedResourceForecastAnalysisU004Error(RuntimeError):
    """One side of the U002/U004 authority boundary is invalid."""


def _fail(message: str) -> NoReturn:
    raise LearnedResourceForecastAnalysisU004Error(message)


def _load_script(module_name: str, filename: str) -> Any:
    path = REPOSITORY / "scripts" / filename
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        _fail(f"cannot load frozen script: {filename}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_BASE = _load_script(
    "acfqp_u002_analysis_for_u004",
    "run_learned_resource_forecast_analysis_u002.py",
)
_U002_PREPARE = _load_script(
    "acfqp_u002_prepare_for_u004_analysis",
    "prepare_learned_resource_forecast_campaign_u002.py",
)
_U004_PREPARE = _load_script(
    "acfqp_u004_prepare_for_u004_analysis",
    "prepare_learned_resource_forecast_evidence_successor_u004.py",
)


def _read_json(path: Path, *, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise LearnedResourceForecastAnalysisU004Error(
            f"cannot read {label}: {path}"
        ) from error
    if type(value) is not dict:
        _fail(f"{label} must contain one JSON object")
    return value


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="operation", required=True)

    def authority(command: argparse.ArgumentParser) -> None:
        command.add_argument("--predecessor-protocol", type=Path, required=True)
        command.add_argument("--predecessor-manifest", type=Path, required=True)
        command.add_argument("--protocol", type=Path, required=True)
        command.add_argument("--manifest", type=Path, required=True)

    fit = commands.add_parser("fit-encoders")
    authority(fit)
    fit.add_argument("--trajectory-dir", type=Path, action="append", required=True)
    fit.add_argument("--output-dir", type=Path, required=True)
    fit.add_argument("--device", default="cuda:0")

    encode = commands.add_parser("encode-probes")
    authority(encode)
    encode.add_argument("--probe-dir", type=Path, action="append", required=True)
    encode.add_argument("--aligned-encoder", type=Path, required=True)
    encode.add_argument("--shuffled-encoder", type=Path, required=True)
    encode.add_argument("--output-dir", type=Path, required=True)
    encode.add_argument("--device", default="cuda:0")

    evaluate = commands.add_parser("evaluate")
    authority(evaluate)
    evaluate.add_argument(
        "--predecessor-status-dir", type=Path, action="append", required=True
    )
    evaluate.add_argument("--status-dir", type=Path, action="append", required=True)
    evaluate.add_argument(
        "--predecessor-training-result-dir",
        type=Path,
        action="append",
        required=True,
    )
    evaluate.add_argument(
        "--evidence-dir",
        "--worker-result-dir",
        dest="worker_result_dir",
        type=Path,
        action="append",
        required=True,
    )
    evaluate.add_argument("--matrix", type=Path, required=True)
    evaluate.add_argument("--matrix-metadata", type=Path, required=True)
    evaluate.add_argument("--encoder-receipt-dir", type=Path, required=True)
    evaluate.add_argument("--label-dir", type=Path, action="append", required=True)
    evaluate.add_argument("--output", type=Path, required=True)
    return parser


def _arguments(argv: Sequence[str] | None = None) -> argparse.Namespace:
    return _build_parser().parse_args(argv)


def _load_protocols(args: argparse.Namespace) -> tuple[dict[str, Any], dict[str, Any]]:
    predecessor = validate_ratified_learned_resource_forecast_protocol_v1(
        _read_json(args.predecessor_protocol, label="ratified U002 predecessor protocol")
    )
    successor = (
        validate_ratified_learned_resource_forecast_evidence_successor_protocol_v1(
            _read_json(args.protocol, label="ratified U004 successor protocol")
        )
    )
    authority = successor["predecessor_training_authority"]
    if (
        predecessor["protocol_id"] != U002_PROTOCOL_ID_V1
        or predecessor["source_commit"] != U002_SOURCE_COMMIT_V1
        or predecessor["pilot_execution_identity"] != U002_EXECUTION_IDENTITY_V1
        or authority.get("protocol_id") != predecessor["protocol_id"]
        or authority.get("source_commit") != predecessor["source_commit"]
        or authority.get("pilot_execution_identity")
        != predecessor["pilot_execution_identity"]
        or authority.get("failed_u002_evidence_dispatch_eligible") is not False
        or authority.get("u002_evidence_status_logs_or_artifacts_eligible") is not False
        or authority.get("training_artifacts_are_read_only_inputs") is not True
        or authority.get("training_artifacts_may_be_relabelled_as_u004") is not False
        or authority.get("model_evaluation_tape_prefix")
        != predecessor["evaluation_tape_prefix"]
        or authority.get("model_evaluation_measurements_are_read_only_inputs")
        is not True
        or authority.get("model_evaluation_reexecuted_in_u004") is not False
        or successor["evaluation_tape_prefix"]
        != predecessor["evaluation_tape_prefix"]
    ):
        _fail("U004 protocol does not bind the exact read-only U002 training authority")
    return predecessor, successor


def _validate_dual_manifests(
    predecessor_document: Mapping[str, Any],
    successor_document: Mapping[str, Any],
    *,
    predecessor_protocol: Mapping[str, Any],
    successor_protocol: Mapping[str, Any],
) -> dict[str, Any]:
    expected_predecessor = _U002_PREPARE.build_launch_manifest_v1(
        dict(predecessor_protocol)
    )
    expected_successor = _U004_PREPARE.build_launch_manifest_v1(dict(successor_protocol))
    if type(predecessor_document) is not dict or predecessor_document != expected_predecessor:
        _fail("U002 predecessor manifest differs from its frozen builder output")
    if type(successor_document) is not dict or successor_document != expected_successor:
        _fail("U004 successor manifest differs from its frozen builder output")
    if (
        successor_document.get("schema") != SUCCESSOR_MANIFEST_SCHEMA_V1
        or successor_document.get("protocol_id") != successor_protocol["protocol_id"]
        or successor_document.get("source_commit") != successor_protocol["source_commit"]
        or successor_document.get("pilot_execution_identity")
        != successor_protocol["pilot_execution_identity"]
        or successor_document.get("phase_roster") != ["evidence"]
        or successor_document.get("worker_count") != 6
        or successor_document.get("predecessor_training_authority")
        != successor_protocol["predecessor_training_authority"]
    ):
        _fail("U004 manifest identity or evidence-only phase roster changed")

    training_jobs: dict[str, dict[str, Any]] = {}
    player_jobs: dict[str, dict[str, Any]] = {}
    training_rosters: dict[str, dict[str, Any]] = {}
    evidence_rosters: dict[str, dict[str, Any]] = {}
    for worker_index, (old_worker, new_worker) in enumerate(
        zip(
            predecessor_document["workers"],
            successor_document["workers"],
            strict=True,
        )
    ):
        if (
            old_worker.get("worker") != worker_index
            or new_worker.get("worker") != worker_index
            or old_worker.get("expected_hostname") != new_worker.get("expected_hostname")
            or old_worker.get("device") != new_worker.get("device")
            or old_worker.get("seeds") != new_worker.get("seeds")
            or len(old_worker.get("policy_training_jobs", ())) != 24
            or len(new_worker.get("predecessor_policy_training_jobs", ())) != 24
            or len(new_worker.get("player_evidence_jobs", ())) != 72
        ):
            _fail("U002/U004 worker ownership or fixed per-worker roster changed")
        training_ids: list[str] = []
        for old_job, bound_job in zip(
            old_worker["policy_training_jobs"],
            new_worker["predecessor_policy_training_jobs"],
            strict=True,
        ):
            expected_bound = dict(old_job) | {
                "provenance": "READ_ONLY_U002_TRAINING_AUTHORITY"
            }
            if bound_job != expected_bound:
                _fail("U004 predecessor training roster is not the exact U002 roster")
            execution_id = old_job["execution_id"]
            if execution_id in training_jobs:
                _fail("U002 predecessor training execution ID is duplicated")
            training_jobs[execution_id] = dict(old_job) | {
                "worker": worker_index,
                "expected_hostname": old_worker["expected_hostname"],
                "device": old_worker["device"],
            }
            training_ids.append(execution_id)
        evidence_ids: list[str] = []
        for job in new_worker["player_evidence_jobs"]:
            key = player_key_v1(job["seed"], job["arm"], job["checkpoint"])
            if (
                job.get("player_key") != key
                or job.get("execution_id", "").startswith(
                    f"{U002_EXECUTION_IDENTITY_V1}:player-evidence:"
                )
                or job.get("predecessor_training_execution_id")
                not in training_jobs
                or key in player_jobs
            ):
                _fail("U004 evidence identity or predecessor snapshot binding changed")
            player_jobs[key] = dict(job) | {
                "worker": worker_index,
                "expected_hostname": new_worker["expected_hostname"],
                "device": new_worker["device"],
            }
            evidence_ids.append(job["execution_id"])
        training_name = new_worker["predecessor_training_status_stream"]
        evidence_name = new_worker["player_evidence_status_stream"]
        if training_name != old_worker["policy_training_status_stream"]:
            _fail("U004 predecessor training status basename changed")
        training_rosters[training_name] = {
            "phase": "training",
            "worker": worker_index,
            "execution_ids": tuple(training_ids),
        }
        evidence_rosters[evidence_name] = {
            "phase": "evidence",
            "worker": worker_index,
            "execution_ids": tuple(evidence_ids),
        }
    expected_player_keys = {
        player_key_v1(seed, arm, checkpoint)
        for seed in LEARNED_RESOURCE_FORECAST_TRAINING_SEEDS_V1
        for arm in LEARNED_RESOURCE_FORECAST_ARMS_V1
        for checkpoint in LEARNED_RESOURCE_FORECAST_CHECKPOINTS_V1
    }
    if (
        len(training_jobs) != EXPECTED_TRAINING_JOB_COUNT_V1
        or len(player_jobs) != EXPECTED_PLAYER_COUNT_V1
        or set(player_jobs) != expected_player_keys
        or len(training_rosters) != 6
        or len(evidence_rosters) != 6
        or successor_document.get("expected_counts")
        != {
            "parent_policy_training_jobs": EXPECTED_TRAINING_JOB_COUNT_V1,
            "parent_model_snapshots": EXPECTED_MODEL_SNAPSHOT_COUNT_V1,
            "successor_player_evidence_jobs": EXPECTED_PLAYER_COUNT_V1,
            "trajectory_player_artifacts": 288,
            "complete_trajectory_episodes": 4_608,
            "label_aggregates": EXPECTED_PLAYER_COUNT_V1,
            "exact_eight_action_probe_records": 6_912,
        }
    ):
        _fail("dual-authority manifest does not close the frozen 144/432 roster")
    return {
        "document": dict(successor_document),
        "predecessor_document": dict(predecessor_document),
        "training_jobs": training_jobs,
        "player_jobs": player_jobs,
        "training_stream_rosters": training_rosters,
        "evidence_stream_rosters": evidence_rosters,
    }


def _resolve_unique(directories: Sequence[Path], basename: str, *, label: str) -> Path:
    matches = [directory / basename for directory in directories]
    matches = [path for path in matches if path.is_file()]
    if len(matches) != 1:
        _fail(f"{label} must resolve exactly once: {basename}")
    return matches[0]


def _validate_status_stream(
    directories: Sequence[Path], basename: str, roster: Mapping[str, Any]
) -> int:
    path = _resolve_unique(directories, basename, label="worker status stream")
    try:
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    except (OSError, json.JSONDecodeError) as error:
        raise LearnedResourceForecastAnalysisU004Error(
            f"cannot read exact worker status stream: {path}"
        ) from error
    expected = tuple(roster["execution_ids"])
    phase, worker = roster["phase"], roster["worker"]
    if (
        not rows
        or any(type(row) is not dict for row in rows)
        or rows[0].get("event") != "WORKER_STARTED"
        or rows[-1].get("event") != "WORKER_COMPLETED"
        or sum(row.get("event") == "WORKER_STARTED" for row in rows) != 1
        or sum(row.get("event") == "WORKER_COMPLETED" for row in rows) != 1
        or any(row.get("event") in {"JOB_FAILED", "WORKER_FAILED"} for row in rows)
        or any(row.get("phase") != phase or row.get("worker") != worker for row in rows)
        or any(
            row.get("event")
            not in {"WORKER_STARTED", "JOB_STARTED", "JOB_COMPLETED", "WORKER_COMPLETED"}
            for row in rows
        )
        or rows[-1].get("completed_job_count") != len(expected)
    ):
        _fail("worker status lifecycle did not close under its own authority")
    started = [row for row in rows if row.get("event") == "JOB_STARTED"]
    completed = [row for row in rows if row.get("event") == "JOB_COMPLETED"]
    if (
        [row.get("execution_id") for row in started] != list(expected)
        or [row.get("execution_id") for row in completed] != list(expected)
        or [row.get("job_ordinal") for row in started] != list(range(len(expected)))
        or [row.get("job_ordinal") for row in completed] != list(range(len(expected)))
        or any(row.get("preexecution_identity_check_only") is not False for row in started)
        or any(
            row.get("completed_job_count") != index + 1
            or row.get("expected_job_count") != len(expected)
            for index, row in enumerate(completed)
        )
    ):
        _fail("worker status identities are missing, duplicated, reordered, or foreign")
    return len(completed)


def _expected_worker_files(
    manifest: Mapping[str, Any], worker_index: int
) -> tuple[set[str], set[str]]:
    predecessor: set[str] = set()
    successor: set[str] = set()
    old_worker = manifest["predecessor_document"]["workers"][worker_index]
    new_worker = manifest["document"]["workers"][worker_index]
    for job in old_worker["policy_training_jobs"]:
        predecessor.add(job["result_filename"])
        predecessor.update(job["checkpoint_filenames"])
    for job in new_worker["player_evidence_jobs"]:
        successor.update((job["label_filename"], job["probe_filename"]))
        if job["split"] == "TRAIN":
            successor.update(
                (job["trajectory_metadata_filename"], job["trajectory_array_filename"])
            )
    return predecessor, successor


def _validate_exact_directory(directory: Path, expected: set[str], *, label: str) -> None:
    try:
        entries = tuple(directory.iterdir())
    except OSError as error:
        raise LearnedResourceForecastAnalysisU004Error(
            f"cannot scan {label}: {directory}"
        ) from error
    actual = {entry.name for entry in entries if entry.is_file()}
    if any(not entry.is_file() for entry in entries) or len(actual) != len(entries) or actual != expected:
        _fail(f"{label} has missing, foreign, or non-file artifacts")


def _ownership_validator(
    predecessor_protocol: Mapping[str, Any], successor_protocol: Mapping[str, Any]
):
    def validate(
        document: Mapping[str, Any], *, protocol: Mapping[str, Any], job: Mapping[str, Any]
    ) -> None:
        expected_identity = {
            "player_key": job["player_key"],
            "base_training_seed": job["seed"],
            "generator_arm": job["arm"],
            "checkpoint_environment_interactions": job["checkpoint"],
            "split": job["split"],
            "generator_arm_checkpoint_seed_are_not_classifier_inputs": True,
        }
        context = document.get("execution_context")
        snapshot = document.get("policy_snapshot")
        if (
            protocol != successor_protocol
            or document.get("protocol_id") != successor_protocol["protocol_id"]
            or document.get("source_commit") != successor_protocol["source_commit"]
            or document.get("pilot_execution_identity")
            != successor_protocol["pilot_execution_identity"]
            or document.get("player_identity") != expected_identity
            or type(context) is not dict
            or context.get("execution_id") != job["execution_id"]
            or context.get("source_commit") != successor_protocol["source_commit"]
            or context.get("hostname") != job["expected_hostname"]
            or context.get("device") != job["device"]
            or type(snapshot) is not dict
            or type(snapshot.get("path")) is not str
            or Path(snapshot["path"]).resolve()
            != (
                Path(
                    successor_protocol["predecessor_training_authority"][
                        "results_root"
                    ]
                )
                / f"worker-{job['worker']}"
                / job["model_filename"]
            ).resolve()
            or snapshot.get("artifact_kind")
            != "INFERENCE_ONLY_BARE_ONLINE_STATE_DICT"
            or snapshot.get("predecessor_protocol_id")
            != predecessor_protocol["protocol_id"]
            or snapshot.get("predecessor_source_commit")
            != predecessor_protocol["source_commit"]
            or snapshot.get("predecessor_training_execution_id")
            != job["predecessor_training_execution_id"]
            or snapshot.get("predecessor_pilot_execution_identity")
            != predecessor_protocol["pilot_execution_identity"]
            or snapshot.get("snapshot_is_read_only_predecessor_input") is not True
            or snapshot.get("snapshot_is_u004_training_artifact") is not False
        ):
            _fail("U004 evidence ownership failed the dual-authority snapshot binding")

    return validate


def _install_base_boundary(
    args: argparse.Namespace,
    predecessor_protocol: Mapping[str, Any],
    successor_protocol: Mapping[str, Any],
    manifest: Mapping[str, Any],
) -> None:
    original_training_counts = _BASE._training_artifact_counts  # noqa: SLF001

    def load_protocol(path: Path) -> dict[str, Any]:
        if path.resolve() != args.protocol.resolve():
            _fail("base analysis attempted to open a non-U004 protocol")
        return dict(successor_protocol)

    def load_manifest(path: Path, protocol: Mapping[str, Any]) -> dict[str, Any]:
        if path.resolve() != args.manifest.resolve() or protocol != successor_protocol:
            _fail("base analysis attempted to open a non-U004 manifest")
        return dict(manifest)

    def status_counts(
        _successor_directories: Sequence[Path], internal: Mapping[str, Any]
    ) -> dict[str, int]:
        predecessor_dirs = tuple(args.predecessor_status_dir)
        successor_dirs = tuple(args.status_dir)
        training = sum(
            _validate_status_stream(predecessor_dirs, name, roster)
            for name, roster in internal["training_stream_rosters"].items()
        )
        evidence = sum(
            _validate_status_stream(successor_dirs, name, roster)
            for name, roster in internal["evidence_stream_rosters"].items()
        )
        if training != EXPECTED_TRAINING_JOB_COUNT_V1 or evidence != EXPECTED_PLAYER_COUNT_V1:
            _fail("U002 training and U004 evidence status matrices did not close")
        return {
            "completed_training_jobs": training,
            "failed_training_jobs": 0,
            "model_snapshots": EXPECTED_MODEL_SNAPSHOT_COUNT_V1,
            "completed_player_evidence_jobs": evidence,
            "failed_player_evidence_jobs": 0,
            "missing_identities": 0,
            "duplicate_identities": 0,
            "foreign_identities": 0,
        }

    def training_artifact_counts(
        _successor_directories: Sequence[Path],
        *,
        protocol: Mapping[str, Any],
        manifest: Mapping[str, Any],
    ) -> dict[str, int]:
        if protocol != successor_protocol:
            _fail("training artifact validation received non-U004 analysis authority")
        return original_training_counts(
            tuple(args.predecessor_training_result_dir),
            protocol=predecessor_protocol,
            manifest=manifest,
        )

    def inventory(
        successor_directories: Sequence[Path], internal: Mapping[str, Any]
    ) -> None:
        predecessor_dirs = tuple(args.predecessor_training_result_dir)
        if (
            len(predecessor_dirs) != 6
            or len(set(predecessor_dirs)) != 6
            or len(successor_directories) != 6
            or len(set(successor_directories)) != 6
        ):
            _fail("dual inventory requires six distinct U002 and six distinct U004 directories")
        for worker_index in range(6):
            old_expected, new_expected = _expected_worker_files(internal, worker_index)
            _validate_exact_directory(
                predecessor_dirs[worker_index],
                old_expected,
                label="read-only U002 training directory",
            )
            _validate_exact_directory(
                successor_directories[worker_index],
                new_expected,
                label="fresh U004 evidence directory",
            )

    _BASE._load_protocol = load_protocol  # noqa: SLF001
    _BASE._load_manifest = load_manifest  # noqa: SLF001
    _BASE._validate_player_evidence_ownership = _ownership_validator(  # noqa: SLF001
        predecessor_protocol, successor_protocol
    )
    if args.operation == "evaluate":
        _BASE._status_counts = status_counts  # noqa: SLF001
        _BASE._training_artifact_counts = training_artifact_counts  # noqa: SLF001
        _BASE._validate_worker_result_inventory = inventory  # noqa: SLF001


def _run(args: argparse.Namespace) -> dict[str, Any]:
    predecessor, successor = _load_protocols(args)
    manifest = _validate_dual_manifests(
        _read_json(args.predecessor_manifest, label="U002 predecessor manifest"),
        _read_json(args.manifest, label="U004 successor manifest"),
        predecessor_protocol=predecessor,
        successor_protocol=successor,
    )
    _install_base_boundary(args, predecessor, successor, manifest)
    summary = _BASE._run(args)  # noqa: SLF001
    return dict(summary) | {
        "predecessor_protocol_id": predecessor["protocol_id"],
        "predecessor_training_authority_validated": True,
        "successor_protocol_id": successor["protocol_id"],
        "successor_evidence_authority_validated": True,
        "model_evaluation_tape_prefix": predecessor["evaluation_tape_prefix"],
        "model_evaluation_provenance": "READ_ONLY_U002_PREDECESSOR",
        "model_evaluation_reexecuted_in_u004": False,
        "failed_u002_evidence_dispatch_used": False,
    }


def main(argv: Sequence[str] | None = None) -> int:
    try:
        summary = _run(_arguments(argv))
    except (
        LearnedResourceForecastAnalysisU004Error,
        LearnedResourceForecastEvidenceSuccessorProtocolV1Error,
        LearnedResourceForecastProtocolV1Error,
        ScienceExecutionIOV1Error,
        ValueError,
    ) as error:
        raise SystemExit(str(error)) from error
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
