#!/usr/bin/env python3
"""Independently replay U004 under separate training/evidence authorities."""

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

from acfqp.phase3e_ids import canonical_json_bytes
from acfqp.science.execution_io_v1 import ScienceExecutionIOV1Error
from acfqp.science.learned_resource_forecast_evidence_successor_protocol_v1 import (
    U002_EXECUTION_IDENTITY_V1,
    U002_PROTOCOL_ID_V1,
    U002_SOURCE_COMMIT_V1,
    validate_ratified_learned_resource_forecast_evidence_successor_protocol_v1,
)
from acfqp.science.learned_resource_forecast_protocol_v1 import (
    EXPECTED_MODEL_SNAPSHOT_COUNT_V1,
    EXPECTED_PLAYER_COUNT_V1,
    EXPECTED_TRAINING_JOB_COUNT_V1,
    LEARNED_RESOURCE_FORECAST_ARMS_V1,
    LEARNED_RESOURCE_FORECAST_CHECKPOINTS_V1,
    LEARNED_RESOURCE_FORECAST_TRAINING_SEEDS_V1,
    player_key_v1,
    validate_ratified_learned_resource_forecast_protocol_v1,
)


REPOSITORY = Path(__file__).resolve().parents[1]
VERIFICATION_SCHEMA_U004_V1 = (
    "acfqp.science.learned_resource_forecast_analysis_verification.u004.v1"
)


class LearnedResourceForecastIndependentVerifierU004Error(RuntimeError):
    """The retained U002-training/U004-evidence analysis cannot be replayed."""


def _fail(message: str) -> NoReturn:
    raise LearnedResourceForecastIndependentVerifierU004Error(message)


def _load_script(module_name: str, filename: str) -> Any:
    spec = importlib.util.spec_from_file_location(
        module_name, REPOSITORY / "scripts" / filename
    )
    if spec is None or spec.loader is None:
        _fail(f"cannot independently load frozen script: {filename}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_BASE = _load_script(
    "acfqp_u002_independent_verifier_for_u004",
    "verify_learned_resource_forecast_analysis_u002.py",
)
_U002_PREPARE = _load_script(
    "acfqp_u002_prepare_for_u004_independent_verifier",
    "prepare_learned_resource_forecast_campaign_u002.py",
)
_U004_PREPARE = _load_script(
    "acfqp_u004_prepare_for_u004_independent_verifier",
    "prepare_learned_resource_forecast_evidence_successor_u004.py",
)


def _read_json(path: Path, *, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise LearnedResourceForecastIndependentVerifierU004Error(
            f"cannot read {label}: {path}"
        ) from error
    if type(value) is not dict:
        _fail(f"{label} must contain one JSON object")
    return value


def _arguments(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--predecessor-protocol", type=Path, required=True)
    parser.add_argument("--predecessor-manifest", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument(
        "--predecessor-status-dir", type=Path, action="append", required=True
    )
    parser.add_argument("--status-dir", type=Path, action="append", required=True)
    parser.add_argument("--trajectory-dir", type=Path, action="append", required=True)
    parser.add_argument("--probe-dir", type=Path, action="append", required=True)
    parser.add_argument("--label-dir", type=Path, action="append", required=True)
    parser.add_argument("--encoder-dir", type=Path, required=True)
    parser.add_argument(
        "--predecessor-training-result-dir",
        type=Path,
        action="append",
        required=True,
    )
    parser.add_argument(
        "--evidence-dir",
        "--worker-result-dir",
        dest="worker_result_dir",
        type=Path,
        action="append",
        required=True,
    )
    parser.add_argument("--matrix", type=Path, required=True)
    parser.add_argument("--matrix-metadata", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--device", default="cuda:0")
    return parser.parse_args(argv)


def _validate_protocol_pair(
    predecessor: Mapping[str, Any], successor: Mapping[str, Any]
) -> None:
    authority = successor.get("predecessor_training_authority")
    if (
        predecessor.get("protocol_id") != U002_PROTOCOL_ID_V1
        or predecessor.get("source_commit") != U002_SOURCE_COMMIT_V1
        or predecessor.get("pilot_execution_identity") != U002_EXECUTION_IDENTITY_V1
        or type(authority) is not dict
        or authority.get("protocol_id") != predecessor["protocol_id"]
        or authority.get("source_commit") != predecessor["source_commit"]
        or authority.get("pilot_execution_identity")
        != predecessor["pilot_execution_identity"]
        or authority.get("completed_training_jobs") != EXPECTED_TRAINING_JOB_COUNT_V1
        or authority.get("model_snapshots") != EXPECTED_MODEL_SNAPSHOT_COUNT_V1
        or authority.get("failed_u002_evidence_dispatch_eligible") is not False
        or authority.get("u002_evidence_status_logs_or_artifacts_eligible") is not False
        or authority.get("training_artifacts_are_read_only_inputs") is not True
        or authority.get("training_artifacts_may_be_relabelled_as_u004") is not False
        or authority.get("model_evaluation_tape_prefix")
        != predecessor["evaluation_tape_prefix"]
        or authority.get("model_evaluation_measurements_are_read_only_inputs")
        is not True
        or authority.get("model_evaluation_reexecuted_in_u004") is not False
        or successor.get("evaluation_tape_prefix")
        != predecessor["evaluation_tape_prefix"]
    ):
        _fail("independent replay rejected the U002/U004 protocol authority pair")


def _replay_dual_manifest(
    predecessor_document: Mapping[str, Any],
    successor_document: Mapping[str, Any],
    *,
    predecessor_protocol: Mapping[str, Any],
    successor_protocol: Mapping[str, Any],
) -> dict[str, Any]:
    if predecessor_document != _U002_PREPARE.build_launch_manifest_v1(
        dict(predecessor_protocol)
    ):
        _fail("independent replay rejected the U002 predecessor manifest")
    if successor_document != _U004_PREPARE.build_launch_manifest_v1(
        dict(successor_protocol)
    ):
        _fail("independent replay rejected the U004 successor manifest")
    if (
        successor_document.get("phase_roster") != ["evidence"]
        or successor_document.get("worker_count") != 6
        or successor_document.get("protocol_id") != successor_protocol["protocol_id"]
        or successor_document.get("predecessor_training_authority")
        != successor_protocol["predecessor_training_authority"]
    ):
        _fail("independent replay rejected the successor identity or phase roster")

    training: dict[str, dict[str, Any]] = {}
    players: dict[str, dict[str, Any]] = {}
    training_rosters: dict[str, dict[str, Any]] = {}
    evidence_rosters: dict[str, dict[str, Any]] = {}
    for worker_index in range(6):
        old_worker = predecessor_document["workers"][worker_index]
        new_worker = successor_document["workers"][worker_index]
        if (
            old_worker.get("worker") != worker_index
            or new_worker.get("worker") != worker_index
            or old_worker.get("expected_hostname") != new_worker.get("expected_hostname")
            or old_worker.get("device") != new_worker.get("device")
            or old_worker.get("seeds") != new_worker.get("seeds")
        ):
            _fail("independent worker ownership replay failed")
        training_ids = []
        old_jobs = old_worker.get("policy_training_jobs")
        bound_jobs = new_worker.get("predecessor_policy_training_jobs")
        if type(old_jobs) is not list or type(bound_jobs) is not list or len(old_jobs) != 24 or len(bound_jobs) != 24:
            _fail("independent predecessor training roster shape changed")
        for old_job, bound_job in zip(old_jobs, bound_jobs, strict=True):
            if bound_job != dict(old_job) | {
                "provenance": "READ_ONLY_U002_TRAINING_AUTHORITY"
            }:
                _fail("independent predecessor training roster replay failed")
            execution = old_job["execution_id"]
            if execution in training:
                _fail("independent replay found duplicate predecessor training ID")
            training[execution] = dict(old_job) | {
                "worker": worker_index,
                "expected_hostname": old_worker["expected_hostname"],
                "device": old_worker["device"],
            }
            training_ids.append(execution)
        evidence_jobs = new_worker.get("player_evidence_jobs")
        if type(evidence_jobs) is not list or len(evidence_jobs) != 72:
            _fail("independent successor evidence roster shape changed")
        evidence_ids = []
        for job in evidence_jobs:
            key = player_key_v1(job["seed"], job["arm"], job["checkpoint"])
            if (
                job.get("player_key") != key
                or job.get("predecessor_training_execution_id") not in training
                or job.get("execution_id", "").startswith(
                    f"{U002_EXECUTION_IDENTITY_V1}:player-evidence:"
                )
                or key in players
            ):
                _fail("independent successor evidence identity replay failed")
            players[key] = dict(job) | {
                "worker": worker_index,
                "expected_hostname": new_worker["expected_hostname"],
                "device": new_worker["device"],
            }
            evidence_ids.append(job["execution_id"])
        training_name = new_worker["predecessor_training_status_stream"]
        evidence_name = new_worker["player_evidence_status_stream"]
        if training_name != old_worker["policy_training_status_stream"]:
            _fail("independent predecessor status basename replay failed")
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
    expected_keys = tuple(
        player_key_v1(seed, arm, checkpoint)
        for seed in LEARNED_RESOURCE_FORECAST_TRAINING_SEEDS_V1
        for arm in LEARNED_RESOURCE_FORECAST_ARMS_V1
        for checkpoint in LEARNED_RESOURCE_FORECAST_CHECKPOINTS_V1
    )
    if (
        len(training) != EXPECTED_TRAINING_JOB_COUNT_V1
        or len(players) != EXPECTED_PLAYER_COUNT_V1
        or set(players) != set(expected_keys)
        or len(training_rosters) != 6
        or len(evidence_rosters) != 6
    ):
        _fail("independent dual manifest did not close 144 training and 432 players")
    ordered_players = {key: players[key] for key in expected_keys}
    return {
        "document": dict(successor_document),
        "predecessor_document": dict(predecessor_document),
        "training": training,
        "players": ordered_players,
        "training_stream_rosters": training_rosters,
        "evidence_stream_rosters": evidence_rosters,
    }


def _resolve(directories: Sequence[Path], basename: str, *, label: str) -> Path:
    matches = [directory / basename for directory in directories]
    matches = [path for path in matches if path.is_file()]
    if len(matches) != 1:
        _fail(f"{label} must resolve exactly once: {basename}")
    return matches[0]


def _replay_stream(
    directories: Sequence[Path], basename: str, roster: Mapping[str, Any]
) -> int:
    path = _resolve(directories, basename, label="independent worker status")
    try:
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    except (OSError, json.JSONDecodeError) as error:
        raise LearnedResourceForecastIndependentVerifierU004Error(
            "independent worker status is unreadable JSONL"
        ) from error
    expected = tuple(roster["execution_ids"])
    if (
        not rows
        or any(type(row) is not dict for row in rows)
        or rows[0].get("event") != "WORKER_STARTED"
        or rows[-1].get("event") != "WORKER_COMPLETED"
        or sum(row.get("event") == "WORKER_STARTED" for row in rows) != 1
        or sum(row.get("event") == "WORKER_COMPLETED" for row in rows) != 1
        or any(row.get("event") in {"JOB_FAILED", "WORKER_FAILED"} for row in rows)
        or any(
            row.get("phase") != roster["phase"]
            or row.get("worker") != roster["worker"]
            for row in rows
        )
        or any(
            row.get("event")
            not in {"WORKER_STARTED", "JOB_STARTED", "JOB_COMPLETED", "WORKER_COMPLETED"}
            for row in rows
        )
        or rows[-1].get("completed_job_count") != len(expected)
    ):
        _fail("independent worker lifecycle closure failed")
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
        _fail("independent worker identity closure failed")
    return len(completed)


def _expected_files(
    manifest: Mapping[str, Any], worker_index: int
) -> tuple[set[str], set[str]]:
    old_expected: set[str] = set()
    new_expected: set[str] = set()
    for job in manifest["predecessor_document"]["workers"][worker_index][
        "policy_training_jobs"
    ]:
        old_expected.add(job["result_filename"])
        old_expected.update(job["checkpoint_filenames"])
    for job in manifest["document"]["workers"][worker_index]["player_evidence_jobs"]:
        new_expected.update((job["label_filename"], job["probe_filename"]))
        if job["split"] == "TRAIN":
            new_expected.update(
                (job["trajectory_metadata_filename"], job["trajectory_array_filename"])
            )
    return old_expected, new_expected


def _exact_inventory(directory: Path, expected: set[str], *, label: str) -> None:
    try:
        entries = tuple(directory.iterdir())
    except OSError as error:
        raise LearnedResourceForecastIndependentVerifierU004Error(
            f"cannot scan {label}"
        ) from error
    actual = {entry.name for entry in entries if entry.is_file()}
    if any(not entry.is_file() for entry in entries) or len(actual) != len(entries) or actual != expected:
        _fail(f"{label} failed its exact allowlist")


def _ownership_validator(
    predecessor_protocol: Mapping[str, Any], successor_protocol: Mapping[str, Any]
):
    def replay(
        document: Mapping[str, Any], *, protocol: Mapping[str, Any], job: Mapping[str, Any]
    ) -> None:
        context = document.get("execution_context")
        snapshot = document.get("policy_snapshot")
        expected_identity = {
            "player_key": job["player_key"],
            "base_training_seed": job["seed"],
            "generator_arm": job["arm"],
            "checkpoint_environment_interactions": job["checkpoint"],
            "split": job["split"],
            "generator_arm_checkpoint_seed_are_not_classifier_inputs": True,
        }
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
            _fail("independent evidence replay rejected the predecessor snapshot binding")

    return replay


def _install_boundary(
    args: argparse.Namespace,
    predecessor_protocol: Mapping[str, Any],
    successor_protocol: Mapping[str, Any],
    manifest: Mapping[str, Any],
) -> None:
    original_training = _BASE._replay_training_artifacts  # noqa: SLF001
    original_write = _BASE.write_exclusive_bytes_v1

    def validate_successor(value: Mapping[str, Any]) -> dict[str, Any]:
        validated = validate_ratified_learned_resource_forecast_evidence_successor_protocol_v1(
            value
        )
        if validated != successor_protocol:
            _fail("base verifier opened a different U004 protocol")
        return validated

    def manifest_replay(
        document: Mapping[str, Any], protocol: Mapping[str, Any]
    ) -> dict[str, Any]:
        if document != manifest["document"] or protocol != successor_protocol:
            _fail("base verifier opened a different U004 manifest")
        return dict(manifest)

    def status_replay(
        _successor_dirs: Sequence[Path], internal: Mapping[str, Any]
    ) -> dict[str, int]:
        training = sum(
            _replay_stream(tuple(args.predecessor_status_dir), name, roster)
            for name, roster in internal["training_stream_rosters"].items()
        )
        evidence = sum(
            _replay_stream(tuple(args.status_dir), name, roster)
            for name, roster in internal["evidence_stream_rosters"].items()
        )
        if training != EXPECTED_TRAINING_JOB_COUNT_V1 or evidence != EXPECTED_PLAYER_COUNT_V1:
            _fail("independent status replay did not close both authorities")
        return {
            "completed_training_jobs": training,
            "failed_training_jobs": 0,
            "model_snapshots": 0,
            "completed_player_evidence_jobs": evidence,
            "failed_player_evidence_jobs": 0,
            "missing_identities": 0,
            "duplicate_identities": 0,
            "foreign_identities": 0,
        }

    def training_replay(
        _successor_dirs: Sequence[Path],
        *,
        protocol: Mapping[str, Any],
        manifest: Mapping[str, Any],
    ) -> tuple[int, int]:
        if protocol != successor_protocol:
            _fail("independent training replay received a foreign successor protocol")
        return original_training(
            tuple(args.predecessor_training_result_dir),
            protocol=predecessor_protocol,
            manifest=manifest,
        )

    def inventory(successor_dirs: Sequence[Path], internal: Mapping[str, Any]) -> None:
        predecessor_dirs = tuple(args.predecessor_training_result_dir)
        if (
            len(predecessor_dirs) != 6
            or len(set(predecessor_dirs)) != 6
            or len(successor_dirs) != 6
            or len(set(successor_dirs)) != 6
        ):
            _fail("independent inventory requires six directories per authority")
        for worker_index in range(6):
            old_expected, new_expected = _expected_files(internal, worker_index)
            _exact_inventory(
                predecessor_dirs[worker_index], old_expected, label="U002 training inventory"
            )
            _exact_inventory(
                successor_dirs[worker_index], new_expected, label="U004 evidence inventory"
            )

    def write(path: Path, data: bytes) -> None:
        if path.name == _BASE.VERIFICATION_FILENAME_V1:
            try:
                document = json.loads(data)
            except (TypeError, json.JSONDecodeError) as error:
                raise LearnedResourceForecastIndependentVerifierU004Error(
                    "independent verification document is not JSON"
                ) from error
            document.update(
                {
                    "schema": VERIFICATION_SCHEMA_U004_V1,
                    "authority_mode": "READ_ONLY_U002_TRAINING_PLUS_FRESH_U004_EVIDENCE",
                    "predecessor_protocol_id": predecessor_protocol["protocol_id"],
                    "predecessor_source_commit": predecessor_protocol["source_commit"],
                    "predecessor_training_authority_validated": True,
                    "successor_protocol_id": successor_protocol["protocol_id"],
                    "successor_evidence_authority_validated": True,
                    "failed_u002_evidence_dispatch_used": False,
                }
            )
            data = canonical_json_bytes(document)
        original_write(path, data)

    _BASE.validate_ratified_learned_resource_forecast_protocol_v1 = validate_successor
    _BASE._replay_manifest = manifest_replay  # noqa: SLF001
    _BASE._replay_evidence_ownership = _ownership_validator(  # noqa: SLF001
        predecessor_protocol, successor_protocol
    )
    _BASE._replay_status = status_replay  # noqa: SLF001
    _BASE._replay_training_artifacts = training_replay  # noqa: SLF001
    _BASE._replay_worker_inventory = inventory  # noqa: SLF001
    _BASE.write_exclusive_bytes_v1 = write


def _verify(args: argparse.Namespace) -> dict[str, Any]:
    predecessor = validate_ratified_learned_resource_forecast_protocol_v1(
        _read_json(args.predecessor_protocol, label="ratified U002 predecessor protocol")
    )
    successor = validate_ratified_learned_resource_forecast_evidence_successor_protocol_v1(
        _read_json(args.protocol, label="ratified U004 successor protocol")
    )
    _validate_protocol_pair(predecessor, successor)
    manifest = _replay_dual_manifest(
        _read_json(args.predecessor_manifest, label="U002 predecessor manifest"),
        _read_json(args.manifest, label="U004 successor manifest"),
        predecessor_protocol=predecessor,
        successor_protocol=successor,
    )
    _install_boundary(args, predecessor, successor, manifest)
    summary = _BASE._verify(args)  # noqa: SLF001
    return dict(summary) | {
        "predecessor_protocol_id": predecessor["protocol_id"],
        "predecessor_training_authority_validated": True,
        "successor_evidence_authority_validated": True,
        "model_evaluation_tape_prefix": predecessor["evaluation_tape_prefix"],
        "model_evaluation_provenance": "READ_ONLY_U002_PREDECESSOR",
        "model_evaluation_reexecuted_in_u004": False,
        "failed_u002_evidence_dispatch_used": False,
    }


def main(argv: Sequence[str] | None = None) -> int:
    try:
        summary = _verify(_arguments(argv))
    except (
        LearnedResourceForecastIndependentVerifierU004Error,
        ScienceExecutionIOV1Error,
        ValueError,
    ) as error:
        raise SystemExit(str(error)) from error
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
