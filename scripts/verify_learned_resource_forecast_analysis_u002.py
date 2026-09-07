#!/usr/bin/env python3
"""Independently replay the retained U002 analysis and its fixed Gate."""

from __future__ import annotations

import os

os.environ["CUBLAS_WORKSPACE_CONFIG"] = ":4096:8"

import argparse
from collections.abc import Mapping, Sequence
import importlib.util
import json
import math
from pathlib import Path
import socket
import sys
from typing import Any, NoReturn

import numpy as np
from scipy.optimize import minimize
from scipy.special import expit

from acfqp.domains import standard_2048
from acfqp.phase3e_ids import canonical_json_bytes
from acfqp.science.early_strategic_signature_2048_pilot_v1 import (
    PolicyTraceV1,
)
from acfqp.science.execution_io_v1 import (
    ScienceExecutionIOV1Error,
    bound_clean_source_commit_v1,
    require_path_outside_repository_v1,
    write_exclusive_bytes_v1,
)
from acfqp.science.learned_resource_forecast_2048_v1 import (
    ALIGNED_TARGET_MODE_V1,
    FORECAST_ENCODER_PARAMETER_COUNT_V1,
    FORECAST_HIDDEN_WIDTH_V1,
    FORECAST_MODEL_PARAMETER_COUNT_V1,
    PLAYER_SHUFFLED_TARGET_MODE_V1,
    aligned_forecast_examples_v1,
    forecast_model_factory_v1,
    frozen_embeddings_v1,
)
from acfqp.science.learned_resource_forecast_evidence_v1 import (
    LABEL_EVIDENCE_SCHEMA_V1,
    PROBE_EVIDENCE_SCHEMA_V1,
    TRAJECTORY_EVIDENCE_SCHEMA_V1,
)
from acfqp.science.learned_resource_forecast_protocol_v1 import (
    ALIGNED_FORECAST_ARM_V1,
    BOOTSTRAP_RANDOM_SEED_V1,
    BOOTSTRAP_REPLICATES_V1,
    EXPECTED_COMPLETE_TRAJECTORY_EPISODE_COUNT_V1,
    EXPECTED_MODEL_SNAPSHOT_COUNT_V1,
    EXPECTED_PLAYER_COUNT_V1,
    EXPECTED_PROBE_RECORD_COUNT_V1,
    EXPECTED_TRAINING_JOB_COUNT_V1,
    EXPECTED_TRAJECTORY_PLAYER_ARTIFACT_COUNT_V1,
    LEARNED_PREFIX_DIMENSION_V1,
    LEARNED_RESOURCE_FORECAST_ARMS_V1,
    LEARNED_RESOURCE_FORECAST_CHECKPOINTS_V1,
    LEARNED_RESOURCE_FORECAST_TEST_SEEDS_V1,
    LEARNED_RESOURCE_FORECAST_TRAINING_SEEDS_V1,
    LEARNED_RESOURCE_FORECAST_TRAIN_SEEDS_V1,
    LOGISTIC_L2_STRENGTH_V1,
    PROBES_PER_PLAYER_V1,
    PROBE_REPRESENTATION_ARMS_V1,
    PROBE_REPRESENTATION_DIMENSIONS_V1,
    RAW_PREFIX_ARM_V1,
    RAW_PREFIX_DIMENSION_V1,
    SHUFFLED_FORECAST_ARM_V1,
    player_key_v1,
    validate_ratified_learned_resource_forecast_protocol_v1,
)
from acfqp.science.matched_double_dqn_2048_learned_resource_pilot_v1 import (
    LEARNED_RESOURCE_POLICY_TRAINING_RESULT_SCHEMA_V1,
    expected_policy_training_execution_id_v1,
    policy_checkpoint_filename_v1,
)
from acfqp.science.matched_2048_env_v1 import initial_state_v1, transition_v1


REPOSITORY = Path(__file__).resolve().parents[1]
VERIFICATION_SCHEMA_V1 = (
    "acfqp.science.learned_resource_forecast_analysis_verification.v1"
)
LAUNCH_MANIFEST_SCHEMA_V1 = (
    "acfqp.science.learned_resource_forecast_2048_launch_manifest.v1"
)
ENCODER_STAGE_RECEIPT_SCHEMA_V1 = (
    "acfqp.science.learned_resource_forecast_encoder_stage_receipt.v1"
)
PROBE_MATRIX_METADATA_SCHEMA_V1 = (
    "acfqp.science.learned_resource_forecast_probe_matrix_metadata.v1"
)
EVALUATION_SCHEMA_V1 = (
    "acfqp.science.learned_resource_forecast_2048_pilot_evaluation.v1"
)
ALIGNED_ENCODER_FILENAME_V1 = "aligned-resource-forecast.encoder.pt"
SHUFFLED_ENCODER_FILENAME_V1 = "player-shuffled-resource-forecast.encoder.pt"
ALIGNED_RECEIPT_FILENAME_V1 = "aligned-resource-forecast.receipt.json"
SHUFFLED_RECEIPT_FILENAME_V1 = (
    "player-shuffled-resource-forecast.receipt.json"
)
MATRIX_FILENAME_V1 = "probe-representation-matrices.npz"
MATRIX_METADATA_FILENAME_V1 = "probe-representation-matrices.metadata.json"
PILOT_RESULT_FILENAME_V1 = "pilot-result.json"
VERIFICATION_FILENAME_V1 = "independent-verification.json"


class LearnedResourceForecastIndependentVerifierV1Error(RuntimeError):
    """The retained staged analysis cannot be independently replayed."""


def _fail(message: str) -> NoReturn:
    raise LearnedResourceForecastIndependentVerifierV1Error(message)


def _analysis_runtime_provenance_v1(
    args: argparse.Namespace, protocol: Mapping[str, Any]
) -> dict[str, str]:
    runtime_commit = getattr(
        args, "analysis_runtime_source_commit", protocol["source_commit"]
    )
    if runtime_commit != bound_clean_source_commit_v1(REPOSITORY):
        _fail("clean verifier runtime checkout differs from its bound source")
    if not hasattr(args, "analysis_runtime_source_commit"):
        return {}
    runtime_protocol_id = getattr(args, "analysis_runtime_protocol_id", None)
    runtime_execution_id = getattr(args, "analysis_runtime_execution_id", None)
    if (
        type(runtime_commit) is not str
        or type(runtime_protocol_id) is not str
        or not runtime_protocol_id
        or type(runtime_execution_id) is not str
        or not runtime_execution_id
    ):
        _fail("explicit verifier runtime authority is incomplete")
    return {
        "measurement_protocol_id": protocol["protocol_id"],
        "measurement_source_commit": protocol["source_commit"],
        "analysis_runtime_protocol_id": runtime_protocol_id,
        "analysis_runtime_source_commit": runtime_commit,
        "analysis_runtime_execution_id": runtime_execution_id,
    }


def _arguments(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--status-dir", type=Path, action="append", required=True)
    parser.add_argument(
        "--trajectory-dir", type=Path, action="append", required=True
    )
    parser.add_argument("--probe-dir", type=Path, action="append", required=True)
    parser.add_argument("--label-dir", type=Path, action="append", required=True)
    parser.add_argument("--encoder-dir", type=Path, required=True)
    parser.add_argument(
        "--worker-result-dir",
        "--model-dir",
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


def _read_json(path: Path, *, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise LearnedResourceForecastIndependentVerifierV1Error(
            f"cannot read {label}: {path}"
        ) from error
    if type(value) is not dict:
        _fail(f"{label} must contain one JSON object")
    return value


def _resolve(
    directories: Sequence[Path], basename: str, *, label: str
) -> Path:
    matches = [directory / basename for directory in directories]
    matches = [path for path in matches if path.is_file()]
    if len(matches) != 1:
        _fail(f"{label} must resolve exactly once: {basename}")
    return matches[0]


def _replay_evidence_ownership(
    document: Mapping[str, Any],
    *,
    protocol: Mapping[str, Any],
    job: Mapping[str, Any],
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
        document.get("source_commit") != protocol["source_commit"]
        or document.get("pilot_execution_identity")
        != protocol["pilot_execution_identity"]
        or document.get("player_identity") != expected_identity
        or type(context) is not dict
        or context.get("execution_id") != job["execution_id"]
        or context.get("source_commit") != protocol["source_commit"]
        or context.get("hostname") != job["expected_hostname"]
        or context.get("device") != job["device"]
        or type(snapshot) is not dict
        or type(snapshot.get("path")) is not str
        or Path(snapshot["path"]).name != job["model_filename"]
        or snapshot.get("artifact_kind")
        != "INFERENCE_ONLY_BARE_ONLINE_STATE_DICT"
    ):
        _fail("evidence ownership failed independent manifest replay")


def _player_order() -> tuple[str, ...]:
    return tuple(
        player_key_v1(seed, arm, checkpoint)
        for seed in LEARNED_RESOURCE_FORECAST_TRAINING_SEEDS_V1
        for arm in LEARNED_RESOURCE_FORECAST_ARMS_V1
        for checkpoint in LEARNED_RESOURCE_FORECAST_CHECKPOINTS_V1
    )


def _replay_manifest(
    document: Mapping[str, Any], protocol: Mapping[str, Any]
) -> dict[str, Any]:
    prepare_path = REPOSITORY / "scripts" / (
        "prepare_learned_resource_forecast_campaign_u002.py"
    )
    spec = importlib.util.spec_from_file_location(
        "acfqp_u002_prepare_for_independent_verifier", prepare_path
    )
    if spec is None or spec.loader is None:
        _fail("cannot load exact launch-manifest builder independently")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    expected_manifest = module.build_launch_manifest_v1(dict(protocol))
    if type(document) is not dict or document != expected_manifest:
        _fail("manifest differs from the exact frozen builder output")
    if (
        document.get("schema") != LAUNCH_MANIFEST_SCHEMA_V1
        or document.get("protocol_id") != protocol["protocol_id"]
        or document.get("source_commit") != protocol["source_commit"]
        or document.get("pilot_execution_identity")
        != protocol["pilot_execution_identity"]
        or document.get("worker_count") != 6
        or type(document.get("workers")) is not list
        or len(document["workers"]) != 6
    ):
        _fail("manifest identity or worker count changed")
    training: dict[str, dict[str, Any]] = {}
    players: dict[str, dict[str, Any]] = {}
    training_streams = []
    evidence_streams = []
    training_stream_rosters: dict[str, dict[str, Any]] = {}
    evidence_stream_rosters: dict[str, dict[str, Any]] = {}
    for worker_index, worker in enumerate(document["workers"]):
        if (
            type(worker) is not dict
            or worker.get("worker") != worker_index
            or type(worker.get("expected_hostname")) is not str
            or type(worker.get("device")) is not str
        ):
            _fail("manifest worker ordinal changed")
        training_streams.append(worker.get("policy_training_status_stream"))
        evidence_streams.append(worker.get("player_evidence_status_stream"))
        training_ids_for_worker: list[str] = []
        evidence_ids_for_worker: list[str] = []
        for job in worker.get("policy_training_jobs", ()):
            if type(job) is not dict:
                _fail("manifest training job changed type")
            seed, arm = job.get("seed"), job.get("arm")
            if (
                seed not in LEARNED_RESOURCE_FORECAST_TRAINING_SEEDS_V1
                or arm not in LEARNED_RESOURCE_FORECAST_ARMS_V1
            ):
                _fail("manifest has a foreign training identity")
            execution = expected_policy_training_execution_id_v1(
                protocol, arm=arm, seed=seed
            )
            checkpoints = [
                policy_checkpoint_filename_v1(
                    arm=arm, seed=seed, checkpoint=checkpoint
                )
                for checkpoint in LEARNED_RESOURCE_FORECAST_CHECKPOINTS_V1
            ]
            if (
                job.get("execution_id") != execution
                or job.get("checkpoint_filenames") != checkpoints
                or job.get("result_filename")
                != f"{arm.lower()}-seed-{seed}.json"
                or execution in training
            ):
                _fail("manifest training job did not replay")
            training[execution] = dict(job) | {
                "worker": worker_index,
                "expected_hostname": worker.get("expected_hostname"),
                "device": worker.get("device"),
            }
            training_ids_for_worker.append(execution)
        for job in worker.get("player_evidence_jobs", ()):
            if type(job) is not dict:
                _fail("manifest player job changed type")
            seed = job.get("seed")
            arm = job.get("arm")
            checkpoint = job.get("checkpoint")
            if (
                seed not in LEARNED_RESOURCE_FORECAST_TRAINING_SEEDS_V1
                or arm not in LEARNED_RESOURCE_FORECAST_ARMS_V1
                or checkpoint not in LEARNED_RESOURCE_FORECAST_CHECKPOINTS_V1
            ):
                _fail("manifest has a foreign player identity")
            key = player_key_v1(seed, arm, checkpoint)
            split = (
                "TRAIN"
                if seed in LEARNED_RESOURCE_FORECAST_TRAIN_SEEDS_V1
                else "TEST"
            )
            stem = f"{arm.lower()}-seed-{seed}-checkpoint-{checkpoint}"
            execution = (
                f"{protocol['pilot_execution_identity']}:player-evidence:{arm}:"
                f"seed:{seed}:checkpoint:{checkpoint}"
            )
            if (
                job.get("player_key") != key
                or job.get("split") != split
                or job.get("execution_id") != execution
                or job.get("model_filename") != f"{stem}.pt"
                or job.get("label_filename") != f"{stem}.label.json"
                or job.get("probe_filename") != f"{stem}.probe.json"
                or job.get("trajectory_metadata_filename")
                != (f"{stem}.trajectory.json" if split == "TRAIN" else None)
                or job.get("trajectory_array_filename")
                != (f"{stem}.trajectory.npz" if split == "TRAIN" else None)
                or key in players
            ):
                _fail("manifest player job did not replay")
            players[key] = dict(job) | {
                "worker": worker_index,
                "expected_hostname": worker.get("expected_hostname"),
                "device": worker.get("device"),
            }
            evidence_ids_for_worker.append(execution)
        if len(training_ids_for_worker) != 24 or len(evidence_ids_for_worker) != 72:
            _fail("manifest worker job count differs from 24/72")
        training_stream_rosters[training_streams[-1]] = {
            "phase": "training",
            "worker": worker_index,
            "execution_ids": tuple(training_ids_for_worker),
        }
        evidence_stream_rosters[evidence_streams[-1]] = {
            "phase": "evidence",
            "worker": worker_index,
            "execution_ids": tuple(evidence_ids_for_worker),
        }
    if (
        len(training) != EXPECTED_TRAINING_JOB_COUNT_V1
        or len(players) != EXPECTED_PLAYER_COUNT_V1
        or tuple(players) != _player_order()
        or any(type(value) is not str for value in training_streams)
        or any(type(value) is not str for value in evidence_streams)
        or len(set(training_streams)) != 6
        or len(set(evidence_streams)) != 6
    ):
        _fail("manifest did not close the exact registered matrices")
    return {
        "document": dict(document),
        "training": training,
        "players": players,
        "training_streams": tuple(training_streams),
        "evidence_streams": tuple(evidence_streams),
        "training_stream_rosters": training_stream_rosters,
        "evidence_stream_rosters": evidence_stream_rosters,
    }


def _replay_runtime_binding(
    manifest: Mapping[str, Any], *, requested_device: str
) -> None:
    import acfqp
    import scipy
    import torch

    document = manifest["document"]
    required = document["required_runtime"]
    central = document["central_analysis"]
    source_path = (REPOSITORY / "src").resolve()
    python_path_entries = os.environ.get("PYTHONPATH", "").split(os.pathsep)
    if (
        ".".join(str(value) for value in sys.version_info[:3])
        != required["python_version"]
        or Path(sys.executable).resolve()
        != Path(required["python_path"]).resolve()
        or np.__version__ != required["numpy_version"]
        or scipy.__version__ != required["scipy_version"]
        or str(torch.__version__) != required["torch_version"]
        or torch.version.cuda != required["torch_cuda_runtime_version"]
        or python_path_entries != [str(source_path)]
        or Path(acfqp.__file__).resolve().parent != source_path / "acfqp"
        or socket.gethostname() != central["expected_hostname"]
        or requested_device != central["device"]
    ):
        _fail(
            "independent Python, dependency tuple, source PYTHONPATH, package "
            "origin, or host differs from the exact manifest"
        )


def _replay_status(
    directories: Sequence[Path], manifest: Mapping[str, Any]
) -> dict[str, int]:
    def stream(basename: str, roster: Mapping[str, Any]) -> int:
        path = _resolve(directories, basename, label="worker status stream")
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError as error:
            raise LearnedResourceForecastIndependentVerifierV1Error(
                "cannot read retained status stream"
            ) from error
        rows: list[dict[str, Any]] = []
        for line in lines:
            try:
                row = json.loads(line)
            except json.JSONDecodeError as error:
                raise LearnedResourceForecastIndependentVerifierV1Error(
                    "status stream is not JSONL"
                ) from error
            if type(row) is not dict:
                _fail("status row is not an object")
            rows.append(row)
        phase = roster["phase"]
        worker = roster["worker"]
        expected = tuple(roster["execution_ids"])
        if (
            not rows
            or rows[0].get("event") != "WORKER_STARTED"
            or rows[-1].get("event") != "WORKER_COMPLETED"
            or sum(row.get("event") == "WORKER_STARTED" for row in rows) != 1
            or sum(row.get("event") == "WORKER_COMPLETED" for row in rows) != 1
            or any(
                row.get("event") in {"JOB_FAILED", "WORKER_FAILED"}
                for row in rows
            )
            or any(
                row.get("phase") != phase or row.get("worker") != worker
                for row in rows
            )
            or any(
                row.get("event")
                not in {
                    "WORKER_STARTED",
                    "JOB_STARTED",
                    "JOB_COMPLETED",
                    "WORKER_COMPLETED",
                }
                for row in rows
            )
            or rows[-1].get("completed_job_count") != len(expected)
        ):
            _fail("worker stream lifecycle failed independent closure")
        started = [row for row in rows if row.get("event") == "JOB_STARTED"]
        completed = [
            row for row in rows if row.get("event") == "JOB_COMPLETED"
        ]
        if (
            [row.get("execution_id") for row in started] != list(expected)
            or [row.get("execution_id") for row in completed] != list(expected)
            or [row.get("job_ordinal") for row in started]
            != list(range(len(expected)))
            or [row.get("job_ordinal") for row in completed]
            != list(range(len(expected)))
            or any(
                row.get("preexecution_identity_check_only") is not False
                for row in started
            )
            or any(
                row.get("completed_job_count") != index + 1
                or row.get("expected_job_count") != len(expected)
                for index, row in enumerate(completed)
            )
        ):
            _fail("worker stream job roster failed independent closure")
        return len(completed)

    training_completed = sum(
        stream(name, roster)
        for name, roster in manifest["training_stream_rosters"].items()
    )
    evidence_completed = sum(
        stream(name, roster)
        for name, roster in manifest["evidence_stream_rosters"].items()
    )
    if (
        training_completed != EXPECTED_TRAINING_JOB_COUNT_V1
        or evidence_completed != EXPECTED_PLAYER_COUNT_V1
    ):
        _fail("twelve worker streams failed independent count closure")
    return {
        "completed_training_jobs": training_completed,
        "failed_training_jobs": 0,
        "model_snapshots": 0,
        "completed_player_evidence_jobs": evidence_completed,
        "failed_player_evidence_jobs": 0,
        "missing_identities": 0,
        "duplicate_identities": 0,
        "foreign_identities": 0,
    }


def _window_starts(transition_count: int) -> tuple[int, ...]:
    if type(transition_count) is not int or transition_count < 8:
        _fail("trajectory has fewer than eight transitions")
    count = transition_count - 8 + 1
    if count <= 32:
        return tuple(range(count))
    return tuple(index * (count - 1) // 31 for index in range(32))


def _replay_training_artifacts(
    directories: Sequence[Path],
    *,
    protocol: Mapping[str, Any],
    manifest: Mapping[str, Any],
) -> tuple[int, int]:
    result_count = 0
    snapshot_count = 0
    for execution, job in manifest["training"].items():
        result_path = _resolve(
            directories, job["result_filename"], label="policy-training result"
        )
        document = _read_json(result_path, label="policy-training result")
        expected_rows = [
            {
                "checkpoint_environment_interactions": checkpoint,
                "filename": filename,
                "artifact_kind": "INFERENCE_ONLY_BARE_ONLINE_STATE_DICT",
            }
            for checkpoint, filename in zip(
                LEARNED_RESOURCE_FORECAST_CHECKPOINTS_V1,
                job["checkpoint_filenames"],
                strict=True,
            )
        ]
        artifact = document.get("artifact_manifest")
        context = document.get("execution_context")
        if (
            document.get("schema")
            != LEARNED_RESOURCE_POLICY_TRAINING_RESULT_SCHEMA_V1
            or document.get("protocol_id") != protocol["protocol_id"]
            or document.get("arm") != job["arm"]
            or document.get("seed") != job["seed"]
            or document.get("device") != job["device"]
            or type(context) is not dict
            or context.get("execution_id") != execution
            or context.get("source_commit") != protocol["source_commit"]
            or context.get("hostname") != job["expected_hostname"]
            or context.get("device") != job["device"]
            or type(artifact) is not dict
            or artifact.get("result_filename") != result_path.name
            or artifact.get("checkpoint_files") != expected_rows
            or artifact.get("checkpoint_file_count") != 3
            or artifact.get("separate_final_model_artifact_written") is not False
        ):
            _fail("policy-training artifacts failed independent identity replay")
        for filename in job["checkpoint_filenames"]:
            _resolve(directories, filename, label="policy snapshot")
            snapshot_count += 1
        result_count += 1
    if (
        result_count != EXPECTED_TRAINING_JOB_COUNT_V1
        or snapshot_count != EXPECTED_MODEL_SNAPSHOT_COUNT_V1
    ):
        _fail("policy-training artifact matrix failed independent closure")
    return result_count, snapshot_count


def _replay_worker_inventory(
    directories: Sequence[Path], manifest: Mapping[str, Any]
) -> None:
    if len(directories) != 6:
        _fail("independent inventory requires six worker directories")
    for worker_index, directory in enumerate(directories):
        expected: set[str] = set()
        worker = manifest["document"]["workers"][worker_index]
        for job in worker["policy_training_jobs"]:
            expected.add(job["result_filename"])
            expected.update(job["checkpoint_filenames"])
        for job in worker["player_evidence_jobs"]:
            expected.update((job["label_filename"], job["probe_filename"]))
            if job["split"] == "TRAIN":
                expected.update(
                    (
                        job["trajectory_metadata_filename"],
                        job["trajectory_array_filename"],
                    )
                )
        try:
            entries = tuple(directory.iterdir())
        except OSError as error:
            raise LearnedResourceForecastIndependentVerifierV1Error(
                "cannot scan independent worker result directory"
            ) from error
        actual = {entry.name for entry in entries if entry.is_file()}
        if (
            any(not entry.is_file() for entry in entries)
            or len(actual) != len(entries)
            or actual != expected
        ):
            _fail("independent worker artifact allowlist did not close exactly")


def _independent_trace_from_summary(
    summary: Mapping[str, Any], *, tape_root: str, episode_index: int
) -> PolicyTraceV1:
    actions = summary.get("accepted_action_indices")
    if (
        type(actions) is not list
        or not actions
        or len(actions) > 20_000
        or any(type(action) is not int for action in actions)
    ):
        _fail("complete episode action sequence failed independent replay")
    state = initial_state_v1(seed=tape_root, episode_index=episode_index)
    states = [state]
    scores: list[int] = []
    digests: list[str] = []
    for decision_index, action in enumerate(actions):
        step = transition_v1(
            state,
            action,
            seed=tape_root,
            episode_index=episode_index,
            decision_index=decision_index,
        )
        state = step.next_state
        states.append(state)
        scores.append(step.merge_score)
        digests.append(step.tape_digest)
    trace = PolicyTraceV1(
        tape_root=tape_root,
        episode_index=episode_index,
        states=tuple(states),
        action_indices=tuple(actions),
        merge_scores=tuple(scores),
        tape_digests=tuple(digests),
        completed_game=(
            state.status is not standard_2048.Swipe2048Status.ACTIVE
        ),
    )
    if (
        any(
            summary.get(name) != value
            for name, value in trace.label_document().items()
        )
        or summary.get("initial_board") != list(states[0].board)
        or summary.get("terminal_board") != list(states[-1].board)
        or summary.get("goal_terminated_episode") is not True
        or summary.get("continue_after_2048") is not False
    ):
        _fail("complete episode summary failed independent transition replay")
    return trace


def _replay_trajectories(
    directories: Sequence[Path],
    *,
    protocol: Mapping[str, Any],
    manifest: Mapping[str, Any],
) -> tuple[set[str], int, int]:
    roots: set[str] = set()
    player_count = 0
    episode_count = 0
    for key in _player_order():
        job = manifest["players"][key]
        if job["split"] != "TRAIN":
            continue
        metadata_path = _resolve(
            directories,
            job["trajectory_metadata_filename"],
            label="trajectory metadata",
        )
        array_path = _resolve(
            directories,
            job["trajectory_array_filename"],
            label="trajectory array",
        )
        document = _read_json(metadata_path, label="trajectory metadata")
        _replay_evidence_ownership(document, protocol=protocol, job=job)
        root = protocol["trajectory_tape_root"]
        summaries = document.get("complete_episode_summaries")
        if (
            document.get("schema") != TRAJECTORY_EVIDENCE_SCHEMA_V1
            or document.get("protocol_id") != protocol["protocol_id"]
            or document.get("player_identity", {}).get("player_key") != key
            or document.get("trajectory_tape_root") != root
            or document.get("complete_episode_count") != 16
            or type(summaries) is not list
            or len(summaries) != 16
            or document.get("skill_label_file_opened") is not False
        ):
            _fail("trajectory metadata failed independent lane replay")
        expected_pairs = []
        replayed_examples = []
        for episode_index, summary in enumerate(summaries):
            if (
                type(summary) is not dict
                or summary.get("episode_index") != episode_index
                or summary.get("goal_terminated_episode") is not True
                or summary.get("continue_after_2048") is not False
                or summary.get("terminal_status") not in {"WON", "LOST"}
            ):
                _fail("trajectory summary is not one complete episode")
            trace = _independent_trace_from_summary(
                summary, tape_root=root, episode_index=episode_index
            )
            episode_examples = aligned_forecast_examples_v1(
                trace, player_id=key
            )
            starts = tuple(
                example.key.window_start for example in episode_examples
            )
            if starts != _window_starts(summary.get("decision_count")):
                raise AssertionError("independent window formula changed")
            if summary.get("forecast_window_count") != len(starts):
                _fail("trajectory window count failed independent formula")
            expected_pairs.extend((episode_index, start) for start in starts)
            replayed_examples.extend(episode_examples)
        try:
            with np.load(array_path, allow_pickle=False) as archive:
                if set(archive.files) != {
                    "tokens",
                    "targets",
                    "episode_index",
                    "window_start",
                }:
                    _fail("trajectory NPZ registry changed")
                tokens = np.asarray(archive["tokens"])
                targets = np.asarray(archive["targets"])
                episodes = np.asarray(archive["episode_index"])
                starts = np.asarray(archive["window_start"])
        except (OSError, ValueError) as error:
            raise LearnedResourceForecastIndependentVerifierV1Error(
                "cannot independently open trajectory NPZ"
            ) from error
        observed = list(zip(episodes.tolist(), starts.tolist(), strict=True))
        if (
            tokens.shape != (len(expected_pairs), 8, 21)
            or targets.shape != (len(expected_pairs), 54)
            or tokens.dtype != np.float32
            or targets.dtype != np.float32
            or episodes.dtype != np.int64
            or starts.dtype != np.int64
            or not np.all(np.isfinite(tokens))
            or not np.all(np.isfinite(targets))
            or observed != expected_pairs
        ):
            _fail("trajectory NPZ failed independent shape or window replay")
        replayed_tokens = np.asarray(
            [example.tokens for example in replayed_examples], dtype=np.float32
        )
        replayed_targets = np.asarray(
            [example.target for example in replayed_examples], dtype=np.float32
        )
        replayed_episodes = np.asarray(
            [example.key.episode_index for example in replayed_examples],
            dtype=np.int64,
        )
        replayed_starts = np.asarray(
            [example.key.window_start for example in replayed_examples],
            dtype=np.int64,
        )
        if (
            not np.array_equal(tokens, replayed_tokens)
            or not np.array_equal(targets, replayed_targets)
            or not np.array_equal(episodes, replayed_episodes)
            or not np.array_equal(starts, replayed_starts)
        ):
            _fail("trajectory NPZ differs from exact snapshot/tape replay")
        roots.add(root)
        player_count += 1
        episode_count += 16
    if (
        player_count != EXPECTED_TRAJECTORY_PLAYER_ARTIFACT_COUNT_V1
        or roots != {protocol["trajectory_tape_root"]}
        or episode_count != EXPECTED_COMPLETE_TRAJECTORY_EPISODE_COUNT_V1
    ):
        _fail("trajectory lane count did not close independently")
    return roots, player_count, episode_count


def _raw_and_tokens(
    row: Mapping[str, Any], *, tape_root: str, episode_index: int
) -> tuple[np.ndarray, tuple[tuple[float, ...], ...]]:
    boards = row.get("boards_s0_through_s8")
    actions = row.get("action_indices_a0_through_a7")
    scores = row.get("merge_scores")
    digests = row.get("spawn_tape_digests")
    if (
        type(boards) is not list
        or len(boards) != 9
        or any(type(board) is not list or len(board) != 16 for board in boards)
        or type(actions) is not list
        or len(actions) != 8
        or type(scores) is not list
        or len(scores) != 8
        or type(digests) is not list
        or len(digests) != 8
    ):
        _fail("probe row shape changed")
    board_tuples = [tuple(board) for board in boards]
    states = tuple(
        standard_2048.state_from_board_v1(board) for board in board_tuples
    )
    if any(type(action) is not int or not 0 <= action < 4 for action in actions):
        _fail("probe action index changed")
    if any(type(score) is not int or score < 0 for score in scores):
        _fail("probe merge score changed")
    if states[0] != initial_state_v1(
        seed=tape_root, episode_index=episode_index
    ):
        _fail("probe initial board differs from independent tape replay")
    for decision_index, action in enumerate(actions):
        replay = transition_v1(
            states[decision_index],
            action,
            seed=tape_root,
            episode_index=episode_index,
            decision_index=decision_index,
        )
        if (
            replay.next_state != states[decision_index + 1]
            or replay.merge_score != scores[decision_index]
            or replay.tape_digest != digests[decision_index]
        ):
            _fail("probe transition differs from independent tape replay")
    normalized_scores = [
        math.log2(score + 1) / standard_2048.GOAL_RANK for score in scores
    ]
    raw = np.asarray(
        [rank / standard_2048.GOAL_RANK for board in board_tuples for rank in board]
        + [float(index == action) for action in actions for index in range(4)]
        + normalized_scores,
        dtype=np.float32,
    )
    tokens = tuple(
        tuple(
            [rank / standard_2048.GOAL_RANK for rank in board_tuples[index]]
            + [float(candidate == actions[index]) for candidate in range(4)]
            + [normalized_scores[index]]
        )
        for index in range(8)
    )
    if raw.shape != (RAW_PREFIX_DIMENSION_V1,):
        raise AssertionError("independent raw prefix dimension changed")
    return raw, tokens


def _replay_probes(
    directories: Sequence[Path],
    *,
    protocol: Mapping[str, Any],
    manifest: Mapping[str, Any],
) -> tuple[np.ndarray, tuple[tuple[tuple[float, ...], ...], ...], set[str]]:
    raw_players = []
    token_rows = []
    roots: set[str] = set()
    for key in _player_order():
        job = manifest["players"][key]
        path = _resolve(directories, job["probe_filename"], label="probe evidence")
        document = _read_json(path, label="probe evidence")
        _replay_evidence_ownership(document, protocol=protocol, job=job)
        root = protocol["probe_tape_root"]
        rows = document.get("probe_rows")
        if (
            document.get("schema") != PROBE_EVIDENCE_SCHEMA_V1
            or document.get("protocol_id") != protocol["protocol_id"]
            or document.get("player_identity", {}).get("player_key") != key
            or document.get("probe_tape_root") != root
            or document.get("probe_count") != 16
            or document.get("exact_accepted_actions_per_probe") != 8
            or document.get("skill_label_or_complete_outcome_included") is not False
            or type(rows) is not list
            or len(rows) != 16
        ):
            _fail("probe document failed independent lane replay")
        player_raw = []
        for episode_index, row in enumerate(rows):
            if (
                type(row) is not dict
                or row.get("episode_index") != episode_index
                or row.get("exact_accepted_action_count") != 8
                or row.get("later_state_or_episode_outcome_included") is not False
            ):
                _fail("probe row identity or eight-action boundary changed")
            raw, tokens = _raw_and_tokens(
                row, tape_root=root, episode_index=episode_index
            )
            if row.get("status_after_eight_actions") != (
                standard_2048.state_from_board_v1(
                    tuple(row["boards_s0_through_s8"][-1])
                ).status.value
            ):
                _fail("probe final status differs from its eighth state")
            player_raw.append(raw)
            token_rows.append(tokens)
        raw_players.append(player_raw)
        roots.add(root)
    raw = np.asarray(raw_players, dtype=np.float32)
    if (
        raw.shape != (EXPECTED_PLAYER_COUNT_V1, 16, RAW_PREFIX_DIMENSION_V1)
        or len(token_rows) != EXPECTED_PROBE_RECORD_COUNT_V1
        or roots != {protocol["probe_tape_root"]}
    ):
        _fail("probe lane count or raw matrix changed")
    return raw, tuple(token_rows), roots


def _load_encoder(path: Path, *, device_name: str) -> Any:
    import torch

    device = torch.device(device_name)
    if device.type == "cuda" and not torch.cuda.is_available():
        _fail("requested verifier CUDA device is unavailable")
    state = torch.load(path, map_location=device, weights_only=True)
    encoder = forecast_model_factory_v1(torch)().encoder.to(device)
    if (
        not isinstance(state, Mapping)
        or set(state) != set(encoder.state_dict())
        or any(not torch.is_tensor(value) for value in state.values())
        or any(not bool(torch.isfinite(value).all()) for value in state.values())
    ):
        _fail("retained encoder is not a finite bare GRU state_dict")
    try:
        encoder.load_state_dict(state, strict=True)
    except RuntimeError as error:
        raise LearnedResourceForecastIndependentVerifierV1Error(
            "retained encoder state shape changed"
        ) from error
    encoder.eval()
    for parameter in encoder.parameters():
        parameter.requires_grad_(False)
    return encoder


def _replay_receipts(
    directory: Path,
    protocol: Mapping[str, Any],
    runtime_provenance: Mapping[str, str] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    runtime_provenance = runtime_provenance or {}
    rows = []
    for receipt_name, mode, encoder_name in (
        (
            ALIGNED_RECEIPT_FILENAME_V1,
            ALIGNED_TARGET_MODE_V1,
            ALIGNED_ENCODER_FILENAME_V1,
        ),
        (
            SHUFFLED_RECEIPT_FILENAME_V1,
            PLAYER_SHUFFLED_TARGET_MODE_V1,
            SHUFFLED_ENCODER_FILENAME_V1,
        ),
    ):
        document = _read_json(directory / receipt_name, label="encoder receipt")
        if (
            not (directory / encoder_name).is_file()
            or document.get("schema") != ENCODER_STAGE_RECEIPT_SCHEMA_V1
            or document.get("protocol_id") != protocol["protocol_id"]
            or document.get("source_commit") != protocol["source_commit"]
            or document.get("pilot_execution_identity")
            != protocol["pilot_execution_identity"]
            or document.get("target_mode") != mode
            or document.get("initialization_seed")
            != protocol["forecast_encoder_contract"]["initialization_seed"]
            or document.get("trajectory_document_count") != 288
            or document.get("complete_trajectory_episode_count") != 4_608
            or document.get("player_count") != 288
            or document.get("encoder_parameter_count")
            != FORECAST_ENCODER_PARAMETER_COUNT_V1
            or document.get("encoder_plus_linear_head_parameter_count")
            != FORECAST_MODEL_PARAMETER_COUNT_V1
            or document.get("fixed_epoch_count") != 50
            or type(document.get("training_loss_by_epoch")) is not list
            or len(document["training_loss_by_epoch"]) != 50
            or any(
                type(value) not in {int, float}
                or not math.isfinite(float(value))
                or float(value) < 0.0
                for value in document["training_loss_by_epoch"]
            )
            or document.get("encoder_state_filename") != encoder_name
            or document.get("encoder_state_is_bare_gru_state_dict") is not True
            or document.get("encoder_frozen") is not True
            or document.get("forecast_head_discarded") is not True
            or document.get("skill_labels_opened_during_training") is not False
            or document.get("CUBLAS_WORKSPACE_CONFIG") != ":4096:8"
            or any(
                document.get(key) != value
                for key, value in runtime_provenance.items()
            )
        ):
            _fail("encoder receipt failed independent replay")
        rows.append(document)
    if rows[0]["example_count"] != rows[1]["example_count"]:
        _fail("encoder receipts used different example support")
    return rows[0], rows[1]


def _replay_matrix(
    matrix_path: Path,
    metadata_path: Path,
    *,
    protocol: Mapping[str, Any],
    runtime_provenance: Mapping[str, str] | None = None,
) -> tuple[dict[str, np.ndarray], dict[str, Any]]:
    runtime_provenance = runtime_provenance or {}
    metadata = _read_json(metadata_path, label="matrix metadata")
    expected_representations = {
        RAW_PREFIX_ARM_V1: {
            "array_key": "raw_prefix",
            "shape": [432, 16, 184],
            "dimension": 184,
        },
        SHUFFLED_FORECAST_ARM_V1: {
            "array_key": "raw_plus_player_shuffled_forecast",
            "shape": [432, 16, 248],
            "dimension": 248,
        },
        ALIGNED_FORECAST_ARM_V1: {
            "array_key": "raw_plus_aligned_resource_forecast",
            "shape": [432, 16, 248],
            "dimension": 248,
        },
    }
    if (
        matrix_path.name != MATRIX_FILENAME_V1
        or metadata_path.name != MATRIX_METADATA_FILENAME_V1
        or metadata.get("schema") != PROBE_MATRIX_METADATA_SCHEMA_V1
        or metadata.get("protocol_id") != protocol["protocol_id"]
        or metadata.get("source_commit") != protocol["source_commit"]
        or metadata.get("matrix_filename") != MATRIX_FILENAME_V1
        or metadata.get("player_keys") != list(_player_order())
        or metadata.get("player_count") != EXPECTED_PLAYER_COUNT_V1
        or metadata.get("probe_document_count") != EXPECTED_PLAYER_COUNT_V1
        or metadata.get("probe_record_count") != EXPECTED_PROBE_RECORD_COUNT_V1
        or metadata.get("probe_tape_roots")
        != [protocol["probe_tape_root"]]
        or metadata.get("representations") != expected_representations
        or metadata.get("encoder_state_files")
        != [ALIGNED_ENCODER_FILENAME_V1, SHUFFLED_ENCODER_FILENAME_V1]
        or metadata.get("encoder_state_count") != 2
        or metadata.get("learned_raw_prefix_blocks_equal_raw") is not True
        or metadata.get("skill_label_path_argument_present") is not False
        or metadata.get("skill_label_file_opened") is not False
        or metadata.get("dtype") != "float32"
        or any(
            metadata.get(key) != value
            for key, value in runtime_provenance.items()
        )
    ):
        _fail("matrix metadata failed independent replay")
    try:
        with np.load(matrix_path, allow_pickle=False) as archive:
            if set(archive.files) != {
                "player_keys",
                "raw_prefix",
                "raw_plus_player_shuffled_forecast",
                "raw_plus_aligned_resource_forecast",
            }:
                _fail("matrix NPZ registry changed")
            keys = np.asarray(archive["player_keys"])
            raw = np.asarray(archive["raw_prefix"])
            shuffled = np.asarray(archive["raw_plus_player_shuffled_forecast"])
            aligned = np.asarray(archive["raw_plus_aligned_resource_forecast"])
    except (OSError, ValueError) as error:
        raise LearnedResourceForecastIndependentVerifierV1Error(
            "cannot open retained matrix NPZ"
        ) from error
    if (
        keys.tolist() != list(_player_order())
        or raw.shape != (432, 16, 184)
        or shuffled.shape != (432, 16, 248)
        or aligned.shape != (432, 16, 248)
        or raw.dtype != np.float32
        or shuffled.dtype != np.float32
        or aligned.dtype != np.float32
        or not np.all(np.isfinite(raw))
        or not np.all(np.isfinite(shuffled))
        or not np.all(np.isfinite(aligned))
        or not np.array_equal(shuffled[:, :, :184], raw)
        or not np.array_equal(aligned[:, :, :184], raw)
    ):
        _fail("matrix arrays failed independent raw-block replay")
    return {
        RAW_PREFIX_ARM_V1: raw,
        SHUFFLED_FORECAST_ARM_V1: shuffled,
        ALIGNED_FORECAST_ARM_V1: aligned,
    }, metadata


def _replay_labels(
    directories: Sequence[Path],
    *,
    protocol: Mapping[str, Any],
    manifest: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], set[str]]:
    rows = []
    roots: set[str] = set()
    for key in _player_order():
        job = manifest["players"][key]
        path = _resolve(directories, job["label_filename"], label="label evidence")
        document = _read_json(path, label="label evidence")
        _replay_evidence_ownership(document, protocol=protocol, job=job)
        root = protocol["label_tape_root"]
        episodes = document.get("complete_episode_summaries")
        score = document.get("skill_score")
        if (
            document.get("schema") != LABEL_EVIDENCE_SCHEMA_V1
            or document.get("protocol_id") != protocol["protocol_id"]
            or document.get("player_identity", {}).get("player_key") != key
            or document.get("label_tape_root") != root
            or document.get("complete_episode_count") != 64
            or type(episodes) is not list
            or len(episodes) != 64
            or type(score) is not dict
            or score.get("episode_count") != 64
            or score.get("kind") != "MEAN_TOTAL_MERGE_SCORE"
            or document.get("skill_class_assigned") is not False
        ):
            _fail("label document failed independent lane replay")
        total = 0
        for episode_index, episode in enumerate(episodes):
            if (
                type(episode) is not dict
                or episode.get("episode_index") != episode_index
                or episode.get("goal_terminated_episode") is not True
                or episode.get("terminal_status") not in {"WON", "LOST"}
                or type(episode.get("total_merge_score")) is not int
            ):
                _fail("label episode failed independent completion replay")
            trace = _independent_trace_from_summary(
                episode, tape_root=root, episode_index=episode_index
            )
            total += trace.total_merge_score
        mean = total / 64
        if (
            score.get("total_merge_score_sum") != total
            or float(score.get("mean_total_merge_score", math.nan)) != mean
        ):
            _fail("label mean did not replay independently")
        rows.append(
            {
                "base_seed": job["seed"],
                "generator_arm": job["arm"],
                "checkpoint": job["checkpoint"],
                "episode_count": 64,
                "mean_total_merge_score": float(mean),
            }
        )
        roots.add(root)
    if (
        len(rows) != EXPECTED_PLAYER_COUNT_V1
        or roots != {protocol["label_tape_root"]}
    ):
        _fail("label lane did not close 432 players")
    return rows, roots


def _nested_matrices(
    arrays: Mapping[str, np.ndarray],
) -> dict[str, dict[str, np.ndarray]]:
    keys = _player_order()
    return {
        arm: {key: arrays[arm][index] for index, key in enumerate(keys)}
        for arm in arrays
    }


def _independent_auroc(labels: np.ndarray, scores: np.ndarray) -> float:
    positive = scores[labels == 1]
    negative = scores[labels == 0]
    if len(positive) == 0 or len(negative) == 0:
        _fail("independent AUROC requires both classes")
    return float(
        (
            np.sum(positive[:, None] > negative[None, :])
            + 0.5 * np.sum(positive[:, None] == negative[None, :])
        )
        / (len(positive) * len(negative))
    )


def _independent_logistic(
    training_features: np.ndarray,
    training_labels: np.ndarray,
    training_players: np.ndarray,
    test_features: np.ndarray,
) -> np.ndarray:
    x_raw = np.asarray(training_features, dtype=np.float64)
    y = np.asarray(training_labels, dtype=np.int64)
    players = np.asarray(training_players, dtype=np.int64)
    x_test_raw = np.asarray(test_features, dtype=np.float64)
    means = np.mean(x_raw, axis=0)
    scales = np.std(x_raw, axis=0, ddof=0)
    scales = np.where(scales == 0.0, 1.0, scales)
    x_train = (x_raw - means) / scales
    x_test = (x_test_raw - means) / scales
    unique_players = np.unique(players)
    player_labels: dict[int, int] = {}
    for player in unique_players:
        rows = y[players == player]
        if len(rows) != PROBES_PER_PLAYER_V1 or not np.all(rows == rows[0]):
            _fail("independent logistic player weighting support changed")
        player_labels[int(player)] = int(rows[0])
    by_class = {
        label: [
            player
            for player, player_label in player_labels.items()
            if player_label == label
        ]
        for label in (0, 1)
    }
    if any(not values for values in by_class.values()):
        _fail("independent logistic requires both training classes")
    weights_per_row = np.asarray(
        [
            0.5 / (len(by_class[int(label)]) * PROBES_PER_PLAYER_V1)
            for label in y
        ],
        dtype=np.float64,
    )
    y_float = y.astype(np.float64)

    def objective(parameters: np.ndarray) -> tuple[float, np.ndarray]:
        coefficients = parameters[:-1]
        intercept = parameters[-1]
        logits = x_train @ coefficients + intercept
        loss = float(
            np.sum(
                weights_per_row
                * (np.logaddexp(0.0, logits) - y_float * logits)
            )
            + 0.5
            * LOGISTIC_L2_STRENGTH_V1
            * np.dot(coefficients, coefficients)
        )
        residual = weights_per_row * (expit(logits) - y_float)
        gradient = np.concatenate(
            (
                x_train.T @ residual
                + LOGISTIC_L2_STRENGTH_V1 * coefficients,
                np.asarray([np.sum(residual)]),
            )
        )
        return loss, gradient

    fit = minimize(
        objective,
        np.zeros(x_train.shape[1] + 1, dtype=np.float64),
        method="L-BFGS-B",
        jac=True,
        options={"maxiter": 1_000, "ftol": 1e-12, "gtol": 1e-8, "maxls": 50},
    )
    if not fit.success or not np.all(np.isfinite(fit.x)):
        _fail(f"independent fixed logistic fit failed: {fit.message}")
    return expit(x_test @ fit.x[:-1] + fit.x[-1])


def _independent_metric_arrays(
    labels: np.ndarray,
    scores: np.ndarray,
    seed_indices: np.ndarray,
    cluster_counts: np.ndarray,
) -> tuple[float, float, np.ndarray, np.ndarray]:
    point_auroc = _independent_auroc(labels, scores)
    point_brier = float(np.mean((scores - labels) ** 2))
    cluster_count = len(LEARNED_RESOURCE_FORECAST_TEST_SEEDS_V1)
    positive_count = np.zeros(cluster_count, dtype=np.float64)
    negative_count = np.zeros(cluster_count, dtype=np.float64)
    squared_error = np.zeros(cluster_count, dtype=np.float64)
    row_count = np.zeros(cluster_count, dtype=np.float64)
    concordance = np.zeros((cluster_count, cluster_count), dtype=np.float64)
    for seed in range(cluster_count):
        in_seed = seed_indices == seed
        positive_count[seed] = np.sum(in_seed & (labels == 1))
        negative_count[seed] = np.sum(in_seed & (labels == 0))
        squared_error[seed] = np.sum((scores[in_seed] - labels[in_seed]) ** 2)
        row_count[seed] = np.sum(in_seed)
    for positive_seed in range(cluster_count):
        positive = scores[
            (seed_indices == positive_seed) & (labels == 1)
        ]
        for negative_seed in range(cluster_count):
            negative = scores[
                (seed_indices == negative_seed) & (labels == 0)
            ]
            if len(positive) and len(negative):
                concordance[positive_seed, negative_seed] = float(
                    np.sum(positive[:, None] > negative[None, :])
                    + 0.5
                    * np.sum(positive[:, None] == negative[None, :])
                )
    positive_total = cluster_counts @ positive_count
    negative_total = cluster_counts @ negative_count
    numerator = np.einsum(
        "bi,ij,bj->b",
        cluster_counts,
        concordance,
        cluster_counts,
        optimize=True,
    )
    denominator = positive_total * negative_total
    bootstrap_auroc = np.full(len(cluster_counts), np.nan, dtype=np.float64)
    valid = denominator > 0
    bootstrap_auroc[valid] = numerator[valid] / denominator[valid]
    bootstrap_brier = (cluster_counts @ squared_error) / (
        cluster_counts @ row_count
    )
    return point_auroc, point_brier, bootstrap_auroc, bootstrap_brier


def _independent_interval(values: np.ndarray) -> dict[str, float]:
    finite = values[np.isfinite(values)]
    if len(finite) == 0:
        _fail("independent bootstrap has no defined metric replicate")
    lower, upper = np.quantile(finite, (0.025, 0.975), method="linear")
    return {"lower": float(lower), "upper": float(upper)}


def _independent_metric_document(
    values: tuple[float, float, np.ndarray, np.ndarray]
) -> dict[str, Any]:
    auroc, brier, bootstrap_auroc, bootstrap_brier = values
    return {
        "auroc": float(auroc),
        "auroc_ci95": _independent_interval(bootstrap_auroc),
        "auroc_defined_bootstrap_replicates": int(
            np.sum(np.isfinite(bootstrap_auroc))
        ),
        "brier": float(brier),
        "brier_ci95": _independent_interval(bootstrap_brier),
    }


def _independent_prerequisite_result(
    protocol: Mapping[str, Any],
    counts: Mapping[str, int],
    keys: Sequence[str],
    scores: Mapping[str, float],
    identities: Mapping[str, tuple[int, str, int]],
    labels: Mapping[str, str],
    lower: float,
    upper: float,
) -> tuple[dict[str, Any], dict[str, bool]]:
    test_keys = [
        key
        for key in keys
        if identities[key][0] in LEARNED_RESOURCE_FORECAST_TEST_SEEDS_V1
    ]
    expert = [key for key in test_keys if labels[key] == "EXPERT"]
    novice = [key for key in test_keys if labels[key] == "NOVICE"]
    expert_clusters = {identities[key][0] for key in expert}
    novice_clusters = {identities[key][0] for key in novice}
    observed = {
        "test_expert_players": len(expert),
        "test_novice_players": len(novice),
        "test_expert_base_seed_clusters": len(expert_clusters),
        "test_novice_base_seed_clusters": len(novice_clusters),
    }
    prerequisites = {
        "exact_144_training_jobs_completed": counts["completed_training_jobs"]
        == EXPECTED_TRAINING_JOB_COUNT_V1,
        "no_training_job_failed": counts["failed_training_jobs"] == 0,
        "exact_432_model_snapshots_present": counts["model_snapshots"]
        == EXPECTED_MODEL_SNAPSHOT_COUNT_V1,
        "exact_288_trajectory_player_artifacts_present": counts[
            "trajectory_player_artifacts"
        ]
        == EXPECTED_TRAJECTORY_PLAYER_ARTIFACT_COUNT_V1,
        "exact_4608_complete_trajectory_episodes_present": counts[
            "complete_trajectory_episodes"
        ]
        == EXPECTED_COMPLETE_TRAJECTORY_EPISODE_COUNT_V1,
        "exact_2_forecast_encoder_receipts_present": counts[
            "forecast_encoder_receipts"
        ]
        == 2,
        "exact_2_frozen_encoder_states_present": counts[
            "frozen_encoder_states"
        ]
        == 2,
        "exact_432_player_evidence_jobs_completed": counts[
            "completed_player_evidence_jobs"
        ]
        == EXPECTED_PLAYER_COUNT_V1,
        "no_player_evidence_job_failed": counts[
            "failed_player_evidence_jobs"
        ]
        == 0,
        "exact_432_label_aggregates_present": counts["label_aggregates"]
        == EXPECTED_PLAYER_COUNT_V1,
        "exact_6912_probe_records_present": counts[
            "exact_eight_action_probe_records"
        ]
        == EXPECTED_PROBE_RECORD_COUNT_V1,
        "no_missing_duplicate_or_foreign_identity": all(
            counts[name] == 0
            for name in (
                "missing_identities",
                "duplicate_identities",
                "foreign_identities",
            )
        ),
        "train_inverted_cdf_thresholds_are_distinct": float(lower)
        < float(upper),
        "test_has_at_least_16_expert_players": len(expert) >= 16,
        "test_has_at_least_16_novice_players": len(novice) >= 16,
        "test_has_at_least_8_expert_base_seed_clusters": len(expert_clusters)
        >= 8,
        "test_has_at_least_8_novice_base_seed_clusters": len(novice_clusters)
        >= 8,
    }
    result = {
        "schema": EVALUATION_SCHEMA_V1,
        "protocol_id": protocol["protocol_id"],
        "source_commit": protocol["source_commit"],
        "pilot_execution_identity": protocol["pilot_execution_identity"],
        "skill_thresholds": {
            "method": "INVERTED_CDF_ON_288_TRAIN_PLAYERS",
            "lower_25_percent": float(lower),
            "upper_75_percent": float(upper),
            "applied_unchanged_to_test": True,
        },
        "policy_labels": [
            {
                "player_key": key,
                "base_seed": identities[key][0],
                "generator_arm": identities[key][1],
                "checkpoint": identities[key][2],
                "split": (
                    "TRAIN"
                    if identities[key][0]
                    in LEARNED_RESOURCE_FORECAST_TRAIN_SEEDS_V1
                    else "TEST"
                ),
                "mean_total_merge_score": scores[key],
                "label": labels[key],
            }
            for key in keys
        ],
        "prerequisite_counts": dict(counts) | observed,
        "prerequisite_components": prerequisites,
        "bootstrap": {
            "kind": "PAIRED_TEST_BASE_SEED_CLUSTER_BOOTSTRAP",
            "cluster_count": 16,
            "replicates": BOOTSTRAP_REPLICATES_V1,
            "random_seed": BOOTSTRAP_RANDOM_SEED_V1,
            "confidence_interval": "PERCENTILE_95_LINEAR_QUANTILE",
        },
        "scientific_success": False,
        "scientific_success_claimed": False,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "SCALAR_CALIBRATION_GATE": "NOT_RUN",
        "BREAK_EVEN_GATE": "NOT_RUN",
        "OFFICIAL_EXECUTION_GATE": "NOT_RUN",
        "official_execution_allowed": False,
    }
    return result, prerequisites


def _independent_prerequisite_failure(result: Mapping[str, Any]) -> dict[str, Any]:
    components = {
        "aligned_probe_auroc_at_least_0_80": False,
        "aligned_probe_auroc_ci95_lower_at_least_0_75": False,
        "aligned_auroc_delta_ci95_lower_positive_vs_raw": False,
        "aligned_auroc_delta_ci95_lower_positive_vs_shuffled": False,
        "aligned_brier_no_greater_than_both_controls": False,
        "aligned_brier_delta_ci95_upper_at_most_0_01_vs_both_controls": False,
    }
    return dict(result) | {
        "test_probe_predictions": [],
        "metrics": None,
        "paired_aligned_comparisons": None,
        "provisional_design_signal_components": components,
        "provisional_design_signal": "FAIL_PREREQUISITE_GATES",
        "PROVISIONAL_DESIGN_SIGNAL_GATE": "FAIL_PREREQUISITE_GATES",
    }


def _independent_evaluate(
    protocol: Mapping[str, Any],
    label_rows: Sequence[Mapping[str, Any]],
    arrays: Mapping[str, np.ndarray],
    counts: Mapping[str, int],
) -> dict[str, Any]:
    keys = _player_order()
    if len(label_rows) != len(keys):
        _fail("independent label roster changed")
    scores: dict[str, float] = {}
    identities: dict[str, tuple[int, str, int]] = {}
    for key, row in zip(keys, label_rows, strict=True):
        expected_key = player_key_v1(
            row["base_seed"], row["generator_arm"], row["checkpoint"]
        )
        if expected_key != key:
            _fail("independent label order or identity changed")
        scores[key] = float(row["mean_total_merge_score"])
        identities[key] = (
            row["base_seed"],
            row["generator_arm"],
            row["checkpoint"],
        )
    train_scores = np.asarray(
        [
            scores[key]
            for key in keys
            if identities[key][0] in LEARNED_RESOURCE_FORECAST_TRAIN_SEEDS_V1
        ],
        dtype=np.float64,
    )
    lower, upper = np.quantile(
        train_scores, (0.25, 0.75), method="inverted_cdf"
    )
    labels = {
        key: (
            "NOVICE"
            if scores[key] <= lower
            else "EXPERT"
            if scores[key] >= upper
            else "EXCLUDED_MIDDLE"
        )
        for key in keys
    }
    early_result, early_prerequisites = _independent_prerequisite_result(
        protocol,
        counts,
        keys,
        scores,
        identities,
        labels,
        float(lower),
        float(upper),
    )
    if not all(early_prerequisites.values()):
        return _independent_prerequisite_failure(early_result)
    train_keys = [
        key
        for key in keys
        if identities[key][0] in LEARNED_RESOURCE_FORECAST_TRAIN_SEEDS_V1
        and labels[key] != "EXCLUDED_MIDDLE"
    ]
    test_keys = [
        key
        for key in keys
        if identities[key][0] in LEARNED_RESOURCE_FORECAST_TEST_SEEDS_V1
        and labels[key] != "EXCLUDED_MIDDLE"
    ]
    numeric = {key: int(labels[key] == "EXPERT") for key in train_keys + test_keys}
    y_train = np.concatenate(
        [
            np.full(PROBES_PER_PLAYER_V1, numeric[key], dtype=np.int64)
            for key in train_keys
        ]
    )
    player_indices = np.concatenate(
        [
            np.full(PROBES_PER_PLAYER_V1, index, dtype=np.int64)
            for index, _key in enumerate(train_keys)
        ]
    )
    predictions: dict[str, dict[str, np.ndarray]] = {}
    for representation in PROBE_REPRESENTATION_ARMS_V1:
        features = np.asarray(arrays[representation], dtype=np.float64)
        x_train = np.concatenate(
            [features[keys.index(key)] for key in train_keys], axis=0
        )
        x_test = np.concatenate(
            [features[keys.index(key)] for key in test_keys], axis=0
        )
        flat = _independent_logistic(
            x_train, y_train, player_indices, x_test
        )
        predictions[representation] = {
            key: flat[
                index * PROBES_PER_PLAYER_V1 : (index + 1)
                * PROBES_PER_PLAYER_V1
            ]
            for index, key in enumerate(test_keys)
        }

    generator = np.random.default_rng(BOOTSTRAP_RANDOM_SEED_V1)
    draws = generator.integers(
        0,
        len(LEARNED_RESOURCE_FORECAST_TEST_SEEDS_V1),
        size=(
            BOOTSTRAP_REPLICATES_V1,
            len(LEARNED_RESOURCE_FORECAST_TEST_SEEDS_V1),
        ),
    )
    cluster_counts = np.zeros(
        (
            BOOTSTRAP_REPLICATES_V1,
            len(LEARNED_RESOURCE_FORECAST_TEST_SEEDS_V1),
        ),
        dtype=np.float64,
    )
    np.add.at(
        cluster_counts,
        (np.arange(BOOTSTRAP_REPLICATES_V1)[:, None], draws),
        1.0,
    )
    seed_to_index = {
        seed: index
        for index, seed in enumerate(LEARNED_RESOURCE_FORECAST_TEST_SEEDS_V1)
    }
    metric_arrays: dict[
        str, dict[str, tuple[float, float, np.ndarray, np.ndarray]]
    ] = {"probe_level": {}, "player_mean_probability": {}}
    for level, player_mean in (
        ("probe_level", False),
        ("player_mean_probability", True),
    ):
        for representation in PROBE_REPRESENTATION_ARMS_V1:
            level_labels: list[int] = []
            level_scores: list[float] = []
            level_seeds: list[int] = []
            for key in test_keys:
                values = predictions[representation][key]
                if player_mean:
                    values = np.asarray([np.mean(values)], dtype=np.float64)
                level_labels.extend([numeric[key]] * len(values))
                level_scores.extend(float(value) for value in values)
                level_seeds.extend(
                    [seed_to_index[identities[key][0]]] * len(values)
                )
            metric_arrays[level][representation] = _independent_metric_arrays(
                np.asarray(level_labels, dtype=np.int64),
                np.asarray(level_scores, dtype=np.float64),
                np.asarray(level_seeds, dtype=np.int64),
                cluster_counts,
            )
    metrics = {
        representation: {
            level: _independent_metric_document(
                metric_arrays[level][representation]
            )
            for level in metric_arrays
        }
        for representation in PROBE_REPRESENTATION_ARMS_V1
    }
    comparisons: dict[str, Any] = {}
    for control in (RAW_PREFIX_ARM_V1, SHUFFLED_FORECAST_ARM_V1):
        comparisons[control] = {}
        for level in metric_arrays:
            candidate = metric_arrays[level][ALIGNED_FORECAST_ARM_V1]
            baseline = metric_arrays[level][control]
            comparisons[control][level] = {
                "aligned_minus_control_auroc": float(
                    candidate[0] - baseline[0]
                ),
                "aligned_minus_control_auroc_ci95": _independent_interval(
                    candidate[2] - baseline[2]
                ),
                "aligned_minus_control_brier": float(
                    candidate[1] - baseline[1]
                ),
                "aligned_minus_control_brier_ci95": _independent_interval(
                    candidate[3] - baseline[3]
                ),
            }

    test_all = [
        key
        for key in keys
        if identities[key][0] in LEARNED_RESOURCE_FORECAST_TEST_SEEDS_V1
    ]
    expert = [key for key in test_all if labels[key] == "EXPERT"]
    novice = [key for key in test_all if labels[key] == "NOVICE"]
    expert_clusters = {identities[key][0] for key in expert}
    novice_clusters = {identities[key][0] for key in novice}
    observed = {
        "test_expert_players": len(expert),
        "test_novice_players": len(novice),
        "test_expert_base_seed_clusters": len(expert_clusters),
        "test_novice_base_seed_clusters": len(novice_clusters),
    }
    prerequisites = {
        "exact_144_training_jobs_completed": counts["completed_training_jobs"]
        == EXPECTED_TRAINING_JOB_COUNT_V1,
        "no_training_job_failed": counts["failed_training_jobs"] == 0,
        "exact_432_model_snapshots_present": counts["model_snapshots"]
        == EXPECTED_MODEL_SNAPSHOT_COUNT_V1,
        "exact_288_trajectory_player_artifacts_present": counts[
            "trajectory_player_artifacts"
        ]
        == EXPECTED_TRAJECTORY_PLAYER_ARTIFACT_COUNT_V1,
        "exact_4608_complete_trajectory_episodes_present": counts[
            "complete_trajectory_episodes"
        ]
        == EXPECTED_COMPLETE_TRAJECTORY_EPISODE_COUNT_V1,
        "exact_2_forecast_encoder_receipts_present": counts[
            "forecast_encoder_receipts"
        ]
        == 2,
        "exact_2_frozen_encoder_states_present": counts[
            "frozen_encoder_states"
        ]
        == 2,
        "exact_432_player_evidence_jobs_completed": counts[
            "completed_player_evidence_jobs"
        ]
        == EXPECTED_PLAYER_COUNT_V1,
        "no_player_evidence_job_failed": counts[
            "failed_player_evidence_jobs"
        ]
        == 0,
        "exact_432_label_aggregates_present": counts["label_aggregates"]
        == EXPECTED_PLAYER_COUNT_V1,
        "exact_6912_probe_records_present": counts[
            "exact_eight_action_probe_records"
        ]
        == EXPECTED_PROBE_RECORD_COUNT_V1,
        "no_missing_duplicate_or_foreign_identity": all(
            counts[name] == 0
            for name in (
                "missing_identities",
                "duplicate_identities",
                "foreign_identities",
            )
        ),
        "train_inverted_cdf_thresholds_are_distinct": float(lower)
        < float(upper),
        "test_has_at_least_16_expert_players": len(expert) >= 16,
        "test_has_at_least_16_novice_players": len(novice) >= 16,
        "test_has_at_least_8_expert_base_seed_clusters": len(expert_clusters)
        >= 8,
        "test_has_at_least_8_novice_base_seed_clusters": len(novice_clusters)
        >= 8,
    }
    result = {
        "schema": EVALUATION_SCHEMA_V1,
        "protocol_id": protocol["protocol_id"],
        "source_commit": protocol["source_commit"],
        "pilot_execution_identity": protocol["pilot_execution_identity"],
        "skill_thresholds": {
            "method": "INVERTED_CDF_ON_288_TRAIN_PLAYERS",
            "lower_25_percent": float(lower),
            "upper_75_percent": float(upper),
            "applied_unchanged_to_test": True,
        },
        "policy_labels": [
            {
                "player_key": key,
                "base_seed": identities[key][0],
                "generator_arm": identities[key][1],
                "checkpoint": identities[key][2],
                "split": (
                    "TRAIN"
                    if identities[key][0]
                    in LEARNED_RESOURCE_FORECAST_TRAIN_SEEDS_V1
                    else "TEST"
                ),
                "mean_total_merge_score": scores[key],
                "label": labels[key],
            }
            for key in keys
        ],
        "prerequisite_counts": dict(counts) | observed,
        "prerequisite_components": prerequisites,
        "bootstrap": {
            "kind": "PAIRED_TEST_BASE_SEED_CLUSTER_BOOTSTRAP",
            "cluster_count": 16,
            "replicates": BOOTSTRAP_REPLICATES_V1,
            "random_seed": BOOTSTRAP_RANDOM_SEED_V1,
            "confidence_interval": "PERCENTILE_95_LINEAR_QUANTILE",
        },
        "scientific_success": False,
        "scientific_success_claimed": False,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "SCALAR_CALIBRATION_GATE": "NOT_RUN",
        "BREAK_EVEN_GATE": "NOT_RUN",
        "OFFICIAL_EXECUTION_GATE": "NOT_RUN",
        "official_execution_allowed": False,
    }
    if not all(prerequisites.values()):
        failed_components = {
            "aligned_probe_auroc_at_least_0_80": False,
            "aligned_probe_auroc_ci95_lower_at_least_0_75": False,
            "aligned_auroc_delta_ci95_lower_positive_vs_raw": False,
            "aligned_auroc_delta_ci95_lower_positive_vs_shuffled": False,
            "aligned_brier_no_greater_than_both_controls": False,
            "aligned_brier_delta_ci95_upper_at_most_0_01_vs_both_controls": False,
        }
        return result | {
            "test_probe_predictions": [],
            "metrics": None,
            "paired_aligned_comparisons": None,
            "provisional_design_signal_components": failed_components,
            "provisional_design_signal": "FAIL_PREREQUISITE_GATES",
            "PROVISIONAL_DESIGN_SIGNAL_GATE": "FAIL_PREREQUISITE_GATES",
        }
    candidate = metrics[ALIGNED_FORECAST_ARM_V1]["probe_level"]
    raw_comparison = comparisons[RAW_PREFIX_ARM_V1]["probe_level"]
    shuffled_comparison = comparisons[SHUFFLED_FORECAST_ARM_V1]["probe_level"]
    components = {
        "aligned_probe_auroc_at_least_0_80": candidate["auroc"] >= 0.80,
        "aligned_probe_auroc_ci95_lower_at_least_0_75": candidate[
            "auroc_ci95"
        ]["lower"]
        >= 0.75,
        "aligned_auroc_delta_ci95_lower_positive_vs_raw": raw_comparison[
            "aligned_minus_control_auroc_ci95"
        ]["lower"]
        > 0.0,
        "aligned_auroc_delta_ci95_lower_positive_vs_shuffled": (
            shuffled_comparison["aligned_minus_control_auroc_ci95"]["lower"]
            > 0.0
        ),
        "aligned_brier_no_greater_than_both_controls": all(
            candidate["brier"] <= metrics[control]["probe_level"]["brier"]
            for control in (RAW_PREFIX_ARM_V1, SHUFFLED_FORECAST_ARM_V1)
        ),
        "aligned_brier_delta_ci95_upper_at_most_0_01_vs_both_controls": all(
            comparisons[control]["probe_level"][
                "aligned_minus_control_brier_ci95"
            ]["upper"]
            <= 0.01
            for control in (RAW_PREFIX_ARM_V1, SHUFFLED_FORECAST_ARM_V1)
        ),
    }
    signal = "PASS" if all(components.values()) else "FAIL"
    return result | {
        "test_probe_predictions": [
            {
                "player_key": key,
                "base_seed": identities[key][0],
                "label": labels[key],
                "probabilities": {
                    representation: [
                        float(value)
                        for value in predictions[representation][key]
                    ]
                    for representation in PROBE_REPRESENTATION_ARMS_V1
                },
            }
            for key in test_keys
        ],
        "metrics": metrics,
        "paired_aligned_comparisons": comparisons,
        "provisional_design_signal_components": components,
        "provisional_design_signal": signal,
        "PROVISIONAL_DESIGN_SIGNAL_GATE": signal,
    }


def _require_exact_replayed_result(
    retained_result: Mapping[str, Any], replayed_result: Mapping[str, Any]
) -> None:
    if (
        retained_result.get("schema") != EVALUATION_SCHEMA_V1
        or retained_result != replayed_result
        or retained_result.get("scientific_success") is not False
        or retained_result.get("scientific_success_claimed") is not False
    ):
        _fail("retained pilot result differs from independent 20k Gate replay")


def _verify(args: argparse.Namespace) -> dict[str, Any]:
    inputs = {
        "protocol": args.protocol,
        "manifest": args.manifest,
        "encoder_dir": args.encoder_dir,
        "matrix": args.matrix,
        "matrix_metadata": args.matrix_metadata,
        "result": args.result,
    }
    resolved = {
        key: require_path_outside_repository_v1(
            repository=REPOSITORY, path=path, label=f"verifier {key} input"
        )
        for key, path in inputs.items()
    }
    status_dirs = [
        require_path_outside_repository_v1(
            repository=REPOSITORY, path=path, label="verifier status directory"
        )
        for path in args.status_dir
    ]
    trajectory_dirs = [
        require_path_outside_repository_v1(
            repository=REPOSITORY, path=path, label="verifier trajectory directory"
        )
        for path in args.trajectory_dir
    ]
    probe_dirs = [
        require_path_outside_repository_v1(
            repository=REPOSITORY, path=path, label="verifier probe directory"
        )
        for path in args.probe_dir
    ]
    label_dirs = [
        require_path_outside_repository_v1(
            repository=REPOSITORY, path=path, label="verifier label directory"
        )
        for path in args.label_dir
    ]
    worker_result_dirs = [
        require_path_outside_repository_v1(
            repository=REPOSITORY,
            path=path,
            label="verifier worker result directory",
        )
        for path in args.worker_result_dir
    ]
    if len(worker_result_dirs) != 6 or len(set(worker_result_dirs)) != 6:
        _fail("verifier requires the six distinct worker result directories")
    output = require_path_outside_repository_v1(
        repository=REPOSITORY, path=args.output, label="verification output"
    )
    if output.name != VERIFICATION_FILENAME_V1 or output.exists():
        _fail("verification output must be fresh independent-verification.json")
    protocol = validate_ratified_learned_resource_forecast_protocol_v1(
        _read_json(resolved["protocol"], label="ratified protocol")
    )
    runtime_provenance = _analysis_runtime_provenance_v1(args, protocol)
    manifest = _replay_manifest(
        _read_json(resolved["manifest"], label="launch manifest"), protocol
    )
    _replay_runtime_binding(manifest, requested_device=args.device)
    status = _replay_status(status_dirs, manifest)
    _replay_worker_inventory(worker_result_dirs, manifest)
    training_results, model_snapshots = _replay_training_artifacts(
        worker_result_dirs, protocol=protocol, manifest=manifest
    )
    status["model_snapshots"] = model_snapshots
    trajectory_roots, trajectory_players, trajectory_episodes = (
        _replay_trajectories(
            trajectory_dirs,
            protocol=protocol,
            manifest=manifest,
        )
    )
    raw_from_probes, token_rows, probe_roots = _replay_probes(
        probe_dirs, protocol=protocol, manifest=manifest
    )
    _replay_receipts(
        resolved["encoder_dir"], protocol, runtime_provenance
    )
    aligned_encoder = _load_encoder(
        resolved["encoder_dir"] / ALIGNED_ENCODER_FILENAME_V1,
        device_name=args.device,
    )
    shuffled_encoder = _load_encoder(
        resolved["encoder_dir"] / SHUFFLED_ENCODER_FILENAME_V1,
        device_name=args.device,
    )
    arrays, metadata = _replay_matrix(
        resolved["matrix"],
        resolved["matrix_metadata"],
        protocol=protocol,
        runtime_provenance=runtime_provenance,
    )
    if not np.array_equal(arrays[RAW_PREFIX_ARM_V1], raw_from_probes):
        _fail("retained raw matrix differs from independent probe reconstruction")
    aligned_embedding = np.asarray(
        frozen_embeddings_v1(aligned_encoder, token_rows), dtype=np.float32
    ).reshape(432, 16, FORECAST_HIDDEN_WIDTH_V1)
    shuffled_embedding = np.asarray(
        frozen_embeddings_v1(shuffled_encoder, token_rows), dtype=np.float32
    ).reshape(432, 16, FORECAST_HIDDEN_WIDTH_V1)
    aligned_difference = float(
        np.max(
            np.abs(
                arrays[ALIGNED_FORECAST_ARM_V1][:, :, 184:] - aligned_embedding
            )
        )
    )
    shuffled_difference = float(
        np.max(
            np.abs(
                arrays[SHUFFLED_FORECAST_ARM_V1][:, :, 184:]
                - shuffled_embedding
            )
        )
    )
    if aligned_difference > 1e-6 or shuffled_difference > 1e-6:
        _fail("retained learned embedding differs from frozen encoder replay")

    # Labels remain the final raw evidence lane opened by the verifier too.
    label_rows, label_roots = _replay_labels(
        label_dirs, protocol=protocol, manifest=manifest
    )
    if (
        trajectory_roots & probe_roots
        or trajectory_roots & label_roots
        or probe_roots & label_roots
    ):
        _fail("trajectory, probe, and label physical tape roots overlap")
    counts = status | {
        "trajectory_player_artifacts": trajectory_players,
        "complete_trajectory_episodes": trajectory_episodes,
        "forecast_encoder_receipts": 2,
        "frozen_encoder_states": metadata["encoder_state_count"],
        "label_aggregates": len(label_rows),
        "exact_eight_action_probe_records": len(token_rows),
    }
    replayed_result = _independent_evaluate(
        protocol, label_rows, arrays, counts
    )
    replayed_result = dict(replayed_result) | runtime_provenance
    retained_result = _read_json(resolved["result"], label="pilot result")
    _require_exact_replayed_result(retained_result, replayed_result)
    verification = {
        "schema": VERIFICATION_SCHEMA_V1,
        "valid": True,
        "protocol_id": protocol["protocol_id"],
        "source_commit": protocol["source_commit"],
        "pilot_execution_identity": protocol["pilot_execution_identity"],
        "manifest_roster_replayed": True,
        "status_counts": status,
        "policy_training_result_document_count": training_results,
        "trajectory_player_count": trajectory_players,
        "complete_trajectory_episode_count": trajectory_episodes,
        "probe_record_count": len(token_rows),
        "label_aggregate_count": len(label_rows),
        "physical_lane_roots_pairwise_disjoint": True,
        "learned_matrix_raw_prefix_blocks_exact": True,
        "raw_matrix_reconstructed_from_probe_json": True,
        "aligned_embedding_maximum_absolute_replay_difference": (
            aligned_difference
        ),
        "shuffled_embedding_maximum_absolute_replay_difference": (
            shuffled_difference
        ),
        "evaluator_20k_cluster_bootstrap_replayed": True,
        "PROVISIONAL_DESIGN_SIGNAL_GATE": retained_result[
            "PROVISIONAL_DESIGN_SIGNAL_GATE"
        ],
        "scientific_success": False,
        "scientific_success_claimed": False,
        **runtime_provenance,
    }
    write_exclusive_bytes_v1(output, canonical_json_bytes(verification))
    return {
        "success": True,
        "valid": True,
        "verification": str(output),
        "protocol_id": protocol["protocol_id"],
        "PROVISIONAL_DESIGN_SIGNAL_GATE": retained_result[
            "PROVISIONAL_DESIGN_SIGNAL_GATE"
        ],
        **runtime_provenance,
    }


def main(argv: Sequence[str] | None = None) -> int:
    try:
        summary = _verify(_arguments(argv))
    except (
        LearnedResourceForecastIndependentVerifierV1Error,
        ScienceExecutionIOV1Error,
        ValueError,
    ) as error:
        raise SystemExit(str(error)) from error
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
