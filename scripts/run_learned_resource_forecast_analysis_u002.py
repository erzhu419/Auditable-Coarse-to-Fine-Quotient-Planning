#!/usr/bin/env python3
"""Run the three irreversible, lane-separated U002 analysis stages."""

from __future__ import annotations

import os

# PyTorch documents this setting as required before the CUDA runtime is
# initialized when deterministic cuBLAS execution is requested.  No module
# imported below imports Torch at module scope.
os.environ["CUBLAS_WORKSPACE_CONFIG"] = ":4096:8"

import argparse
from collections.abc import Mapping, Sequence
import importlib.util
import io
import json
import math
from pathlib import Path
import socket
import sys
from typing import Any, NoReturn

import numpy as np

from acfqp.domains import standard_2048
from acfqp.phase3e_ids import canonical_json_bytes
from acfqp.science.early_strategic_signature_2048_pilot_v1 import PolicyTraceV1
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
    FORECAST_TARGET_DIMENSION_V1,
    PLAYER_SHUFFLED_TARGET_MODE_V1,
    PREFIX_ACTION_COUNT_V1,
    PREFIX_TOKEN_WIDTH_V1,
    ForecastExampleV1,
    ForecastWindowKeyV1,
    aligned_forecast_examples_v1,
    deterministic_window_starts_v1,
    forecast_model_factory_v1,
    frozen_embeddings_v1,
    player_shuffled_targets_v1,
    prefix_tokens_v1,
    raw_prefix_v1,
    train_forecast_encoder_v1,
)
from acfqp.science.learned_resource_forecast_evaluator_v1 import (
    LearnedResourceForecastEvaluatorV1Error,
    evaluate_learned_resource_forecast_pilot_v1,
)
from acfqp.science.learned_resource_forecast_evidence_v1 import (
    LABEL_EVIDENCE_SCHEMA_V1,
    PROBE_EVIDENCE_SCHEMA_V1,
    TRAJECTORY_EVIDENCE_SCHEMA_V1,
)
from acfqp.science.learned_resource_forecast_protocol_v1 import (
    ALIGNED_FORECAST_ARM_V1,
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
    PROBES_PER_PLAYER_V1,
    PROBE_REPRESENTATION_DIMENSIONS_V1,
    RAW_PREFIX_ARM_V1,
    RAW_PREFIX_DIMENSION_V1,
    SHUFFLED_FORECAST_ARM_V1,
    LearnedResourceForecastProtocolV1Error,
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
LAUNCH_MANIFEST_SCHEMA_V1 = (
    "acfqp.science.learned_resource_forecast_2048_launch_manifest.v1"
)
ENCODER_STAGE_RECEIPT_SCHEMA_V1 = (
    "acfqp.science.learned_resource_forecast_encoder_stage_receipt.v1"
)
PROBE_MATRIX_METADATA_SCHEMA_V1 = (
    "acfqp.science.learned_resource_forecast_probe_matrix_metadata.v1"
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

_NPZ_TRAJECTORY_KEYS = frozenset(
    {"tokens", "targets", "episode_index", "window_start"}
)
_NPZ_MATRIX_KEYS = frozenset(
    {
        "player_keys",
        "raw_prefix",
        "raw_plus_player_shuffled_forecast",
        "raw_plus_aligned_resource_forecast",
    }
)


class LearnedResourceForecastAnalysisCLIError(RuntimeError):
    """One staged analysis input, lane boundary, or output is invalid."""


def _fail(message: str) -> NoReturn:
    raise LearnedResourceForecastAnalysisCLIError(message)


def _analysis_runtime_provenance_v1(
    args: argparse.Namespace, protocol: Mapping[str, Any]
) -> dict[str, str]:
    """Validate an optional analysis runtime distinct from measurement source.

    Legacy U002/U004 calls omit these internal Namespace attributes and retain
    the original one-source behavior and artifact schema. U005 supplies all
    three only after validating its separately ratified analysis protocol.
    """

    runtime_commit = getattr(
        args, "analysis_runtime_source_commit", protocol["source_commit"]
    )
    if runtime_commit != bound_clean_source_commit_v1(REPOSITORY):
        _fail("clean analysis runtime checkout differs from its bound source")
    explicit = hasattr(args, "analysis_runtime_source_commit")
    if not explicit:
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
        _fail("explicit analysis runtime authority is incomplete")
    return {
        "measurement_protocol_id": protocol["protocol_id"],
        "measurement_source_commit": protocol["source_commit"],
        "analysis_runtime_protocol_id": runtime_protocol_id,
        "analysis_runtime_source_commit": runtime_commit,
        "analysis_runtime_execution_id": runtime_execution_id,
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="operation", required=True)

    fit = commands.add_parser("fit-encoders")
    fit.add_argument("--protocol", type=Path, required=True)
    fit.add_argument("--manifest", type=Path, required=True)
    fit.add_argument(
        "--trajectory-dir", type=Path, action="append", required=True
    )
    fit.add_argument("--output-dir", type=Path, required=True)
    fit.add_argument("--device", default="cuda:0")

    encode = commands.add_parser("encode-probes")
    encode.add_argument("--protocol", type=Path, required=True)
    encode.add_argument("--manifest", type=Path, required=True)
    encode.add_argument("--probe-dir", type=Path, action="append", required=True)
    encode.add_argument("--aligned-encoder", type=Path, required=True)
    encode.add_argument("--shuffled-encoder", type=Path, required=True)
    encode.add_argument("--output-dir", type=Path, required=True)
    encode.add_argument("--device", default="cuda:0")

    evaluate = commands.add_parser("evaluate")
    evaluate.add_argument("--protocol", type=Path, required=True)
    evaluate.add_argument("--manifest", type=Path, required=True)
    evaluate.add_argument("--status-dir", type=Path, action="append", required=True)
    evaluate.add_argument(
        "--worker-result-dir", type=Path, action="append", required=True
    )
    evaluate.add_argument("--matrix", type=Path, required=True)
    evaluate.add_argument("--matrix-metadata", type=Path, required=True)
    evaluate.add_argument("--encoder-receipt-dir", type=Path, required=True)
    evaluate.add_argument("--label-dir", type=Path, action="append", required=True)
    evaluate.add_argument("--output", type=Path, required=True)
    return parser


def _arguments(argv: Sequence[str] | None = None) -> argparse.Namespace:
    return _build_parser().parse_args(argv)


def _read_json(path: Path, *, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise LearnedResourceForecastAnalysisCLIError(
            f"cannot read {label}: {path}"
        ) from error
    if type(value) is not dict:
        _fail(f"{label} must contain one JSON object")
    return value


def _load_protocol(path: Path) -> dict[str, Any]:
    value = _read_json(path, label="ratified U002 protocol")
    try:
        return validate_ratified_learned_resource_forecast_protocol_v1(value)
    except LearnedResourceForecastProtocolV1Error as error:
        raise LearnedResourceForecastAnalysisCLIError(str(error)) from error


def _expected_player_order() -> tuple[str, ...]:
    return tuple(
        player_key_v1(seed, arm, checkpoint)
        for seed in LEARNED_RESOURCE_FORECAST_TRAINING_SEEDS_V1
        for arm in LEARNED_RESOURCE_FORECAST_ARMS_V1
        for checkpoint in LEARNED_RESOURCE_FORECAST_CHECKPOINTS_V1
    )


def _validate_manifest(
    value: Mapping[str, Any], protocol: Mapping[str, Any]
) -> dict[str, Any]:
    prepare_path = REPOSITORY / "scripts" / (
        "prepare_learned_resource_forecast_campaign_u002.py"
    )
    spec = importlib.util.spec_from_file_location(
        "acfqp_u002_prepare_for_analysis", prepare_path
    )
    if spec is None or spec.loader is None:
        _fail("cannot load the frozen launch-manifest builder")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    expected_manifest = module.build_launch_manifest_v1(dict(protocol))
    if type(value) is not dict or value != expected_manifest:
        _fail("launch manifest differs from the exact frozen builder output")
    if (
        value.get("schema") != LAUNCH_MANIFEST_SCHEMA_V1
        or value.get("protocol_id") != protocol["protocol_id"]
        or value.get("source_commit") != protocol["source_commit"]
        or value.get("pilot_execution_identity")
        != protocol["pilot_execution_identity"]
        or value.get("worker_count") != 6
        or type(value.get("workers")) is not list
        or len(value["workers"]) != 6
    ):
        _fail("launch manifest identity or six-worker shape changed")
    training: dict[str, dict[str, Any]] = {}
    players: dict[str, dict[str, Any]] = {}
    training_streams: list[str] = []
    evidence_streams: list[str] = []
    training_stream_rosters: dict[str, dict[str, Any]] = {}
    evidence_stream_rosters: dict[str, dict[str, Any]] = {}
    for worker_index, worker in enumerate(value["workers"]):
        if (
            type(worker) is not dict
            or worker.get("worker") != worker_index
            or type(worker.get("policy_training_status_stream")) is not str
            or type(worker.get("player_evidence_status_stream")) is not str
            or type(worker.get("policy_training_jobs")) is not list
            or type(worker.get("player_evidence_jobs")) is not list
        ):
            _fail("launch manifest worker roster changed")
        training_streams.append(worker["policy_training_status_stream"])
        evidence_streams.append(worker["player_evidence_status_stream"])
        training_ids_for_worker: list[str] = []
        evidence_ids_for_worker: list[str] = []
        for job in worker["policy_training_jobs"]:
            if type(job) is not dict:
                _fail("launch manifest training job is not an object")
            seed = job.get("seed")
            arm = job.get("arm")
            if (
                seed not in LEARNED_RESOURCE_FORECAST_TRAINING_SEEDS_V1
                or arm not in LEARNED_RESOURCE_FORECAST_ARMS_V1
            ):
                _fail("launch manifest contains a foreign training job")
            execution_id = expected_policy_training_execution_id_v1(
                protocol, arm=arm, seed=seed
            )
            checkpoint_names = [
                policy_checkpoint_filename_v1(
                    arm=arm, seed=seed, checkpoint=checkpoint
                )
                for checkpoint in LEARNED_RESOURCE_FORECAST_CHECKPOINTS_V1
            ]
            if (
                job.get("execution_id") != execution_id
                or job.get("result_filename")
                != f"{arm.lower()}-seed-{seed}.json"
                or job.get("checkpoint_filenames") != checkpoint_names
                or execution_id in training
            ):
                _fail("launch manifest training identity or basename changed")
            training[execution_id] = dict(job) | {
                "worker": worker_index,
                "expected_hostname": worker["expected_hostname"],
                "device": worker["device"],
            }
            training_ids_for_worker.append(execution_id)
        for job in worker["player_evidence_jobs"]:
            if type(job) is not dict:
                _fail("launch manifest player job is not an object")
            seed = job.get("seed")
            arm = job.get("arm")
            checkpoint = job.get("checkpoint")
            if (
                seed not in LEARNED_RESOURCE_FORECAST_TRAINING_SEEDS_V1
                or arm not in LEARNED_RESOURCE_FORECAST_ARMS_V1
                or checkpoint not in LEARNED_RESOURCE_FORECAST_CHECKPOINTS_V1
            ):
                _fail("launch manifest contains a foreign player job")
            key = player_key_v1(seed, arm, checkpoint)
            split = (
                "TRAIN"
                if seed in LEARNED_RESOURCE_FORECAST_TRAIN_SEEDS_V1
                else "TEST"
            )
            stem = f"{arm.lower()}-seed-{seed}-checkpoint-{checkpoint}"
            expected_execution = (
                f"{protocol['pilot_execution_identity']}:player-evidence:{arm}:"
                f"seed:{seed}:checkpoint:{checkpoint}"
            )
            if (
                job.get("player_key") != key
                or job.get("split") != split
                or job.get("execution_id") != expected_execution
                or job.get("model_filename") != f"{stem}.pt"
                or job.get("label_filename") != f"{stem}.label.json"
                or job.get("probe_filename") != f"{stem}.probe.json"
                or job.get("trajectory_metadata_filename")
                != (f"{stem}.trajectory.json" if split == "TRAIN" else None)
                or job.get("trajectory_array_filename")
                != (f"{stem}.trajectory.npz" if split == "TRAIN" else None)
                or key in players
            ):
                _fail("launch manifest player identity or basename changed")
            players[key] = dict(job) | {
                "worker": worker_index,
                "expected_hostname": worker["expected_hostname"],
                "device": worker["device"],
            }
            evidence_ids_for_worker.append(expected_execution)
        if len(training_ids_for_worker) != 24 or len(evidence_ids_for_worker) != 72:
            _fail("launch manifest worker job count differs from 24/72")
        training_stream_rosters[worker["policy_training_status_stream"]] = {
            "phase": "training",
            "worker": worker_index,
            "execution_ids": tuple(training_ids_for_worker),
        }
        evidence_stream_rosters[worker["player_evidence_status_stream"]] = {
            "phase": "evidence",
            "worker": worker_index,
            "execution_ids": tuple(evidence_ids_for_worker),
        }
    if (
        len(training) != EXPECTED_TRAINING_JOB_COUNT_V1
        or len(players) != EXPECTED_PLAYER_COUNT_V1
        or set(players) != set(_expected_player_order())
        or len(set(training_streams)) != 6
        or len(set(evidence_streams)) != 6
        or value.get("expected_counts")
        != {
            "policy_training_jobs": EXPECTED_TRAINING_JOB_COUNT_V1,
            "model_snapshots": EXPECTED_MODEL_SNAPSHOT_COUNT_V1,
            "player_evidence_jobs": EXPECTED_PLAYER_COUNT_V1,
            "trajectory_player_artifacts": (
                EXPECTED_TRAJECTORY_PLAYER_ARTIFACT_COUNT_V1
            ),
            "complete_trajectory_episodes": (
                EXPECTED_COMPLETE_TRAJECTORY_EPISODE_COUNT_V1
            ),
            "label_aggregates": EXPECTED_PLAYER_COUNT_V1,
            "exact_eight_action_probe_records": EXPECTED_PROBE_RECORD_COUNT_V1,
        }
    ):
        _fail("launch manifest does not close the frozen U002 roster")
    return {
        "document": dict(value),
        "training_jobs": training,
        "player_jobs": players,
        "training_status_streams": tuple(training_streams),
        "evidence_status_streams": tuple(evidence_streams),
        "training_stream_rosters": training_stream_rosters,
        "evidence_stream_rosters": evidence_stream_rosters,
    }


def _load_manifest(
    path: Path, protocol: Mapping[str, Any]
) -> dict[str, Any]:
    return _validate_manifest(
        _read_json(path, label="U002 launch manifest"), protocol
    )


def _validate_analysis_runtime(
    manifest: Mapping[str, Any], *, requested_device: str | None
) -> None:
    import acfqp
    import scipy
    import torch

    document = manifest["document"]
    required = document["required_runtime"]
    central = document["central_analysis"]
    python_path_entries = os.environ.get("PYTHONPATH", "").split(os.pathsep)
    expected_source_path = (REPOSITORY / "src").resolve()
    package_file = Path(acfqp.__file__).resolve()
    if (
        ".".join(str(value) for value in sys.version_info[:3])
        != required["python_version"]
        or Path(sys.executable).resolve()
        != Path(required["python_path"]).resolve()
        or np.__version__ != required["numpy_version"]
        or scipy.__version__ != required["scipy_version"]
        or str(torch.__version__) != required["torch_version"]
        or torch.version.cuda != required["torch_cuda_runtime_version"]
        or python_path_entries != [str(expected_source_path)]
        or package_file.parent != expected_source_path / "acfqp"
        or socket.gethostname() != central["expected_hostname"]
        or (
            requested_device is not None
            and requested_device != central["device"]
        )
    ):
        _fail(
            "analysis Python, dependency tuple, source PYTHONPATH, package "
            "origin, host, or device differs from the exact manifest"
        )


def _resolve_unique_file(
    directories: Sequence[Path], basename: str, *, label: str
) -> Path:
    matches = [directory / basename for directory in directories]
    matches = [path for path in matches if path.is_file()]
    if len(matches) != 1:
        _fail(f"{label} must resolve to exactly one file named {basename}")
    return matches[0]


def _validate_player_evidence_ownership(
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
        document.get("player_identity") != expected_identity
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
        _fail("player evidence ownership differs from the manifest worker")


def _replay_complete_episode_summary(
    summary: Mapping[str, Any], *, tape_root: str, episode_index: int
) -> PolicyTraceV1:
    actions = summary.get("accepted_action_indices")
    if (
        type(actions) is not list
        or not actions
        or len(actions) > 20_000
        or any(type(action) is not int for action in actions)
    ):
        _fail("complete episode lacks one exact accepted-action sequence")
    state = initial_state_v1(seed=tape_root, episode_index=episode_index)
    states = [state]
    scores: list[int] = []
    digests: list[str] = []
    for decision_index, action in enumerate(actions):
        replay = transition_v1(
            state,
            action,
            seed=tape_root,
            episode_index=episode_index,
            decision_index=decision_index,
        )
        state = replay.next_state
        states.append(state)
        scores.append(replay.merge_score)
        digests.append(replay.tape_digest)
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
    expected = trace.label_document()
    if (
        any(summary.get(name) != value for name, value in expected.items())
        or summary.get("initial_board") != list(states[0].board)
        or summary.get("terminal_board") != list(states[-1].board)
        or summary.get("goal_terminated_episode") is not True
        or summary.get("continue_after_2048") is not False
    ):
        _fail("complete episode summary differs from exact transition replay")
    return trace


def _trajectory_examples_from_artifacts(
    metadata_path: Path,
    array_path: Path,
    *,
    protocol: Mapping[str, Any],
    job: Mapping[str, Any],
) -> tuple[tuple[ForecastExampleV1, ...], str, int]:
    document = _read_json(metadata_path, label="trajectory metadata")
    key = job["player_key"]
    _validate_player_evidence_ownership(
        document, protocol=protocol, job=job
    )
    expected_root = protocol["trajectory_tape_root"]
    summaries = document.get("complete_episode_summaries")
    if (
        document.get("schema") != TRAJECTORY_EVIDENCE_SCHEMA_V1
        or document.get("protocol_id") != protocol["protocol_id"]
        or document.get("source_commit") != protocol["source_commit"]
        or document.get("pilot_execution_identity")
        != protocol["pilot_execution_identity"]
        or document.get("lane") != "SELF_SUPERVISED_TRAJECTORY"
        or document.get("player_identity", {}).get("player_key") != key
        or document.get("player_identity", {}).get("split") != "TRAIN"
        or document.get("trajectory_tape_root") != expected_root
        or document.get("complete_episode_count") != 16
        or type(summaries) is not list
        or len(summaries) != 16
        or document.get("skill_label_file_opened") is not False
        or document.get("artifact_manifest", {}).get("metadata_filename")
        != metadata_path.name
        or document.get("artifact_manifest", {}).get("compressed_array_filename")
        != array_path.name
        or document.get("artifact_manifest", {}).get(
            "contains_other_lane_content"
        )
        is not False
    ):
        _fail("trajectory metadata differs from its frozen lane identity")
    expected_by_episode: dict[int, tuple[int, ...]] = {}
    replayed_examples: list[ForecastExampleV1] = []
    for expected_index, row in enumerate(summaries):
        if (
            type(row) is not dict
            or row.get("episode_index") != expected_index
            or row.get("goal_terminated_episode") is not True
            or row.get("continue_after_2048") is not False
            or row.get("terminal_status") not in {"WON", "LOST"}
            or type(row.get("decision_count")) is not int
            or row["decision_count"] < PREFIX_ACTION_COUNT_V1
        ):
            _fail("trajectory metadata contains a non-complete episode")
        trace = _replay_complete_episode_summary(
            row, tape_root=expected_root, episode_index=expected_index
        )
        episode_examples = aligned_forecast_examples_v1(
            trace, player_id=key
        )
        starts = tuple(example.key.window_start for example in episode_examples)
        if starts != deterministic_window_starts_v1(row["decision_count"]):
            raise AssertionError("replayed trajectory window formula changed")
        if row.get("forecast_window_count") != len(starts):
            _fail("trajectory metadata window count differs from frozen formula")
        expected_by_episode[expected_index] = starts
        replayed_examples.extend(episode_examples)
    try:
        with np.load(array_path, allow_pickle=False) as archive:
            if set(archive.files) != _NPZ_TRAJECTORY_KEYS:
                _fail("trajectory NPZ member registry changed")
            tokens = np.asarray(archive["tokens"])
            targets = np.asarray(archive["targets"])
            episode_index = np.asarray(archive["episode_index"])
            window_start = np.asarray(archive["window_start"])
    except (OSError, ValueError) as error:
        raise LearnedResourceForecastAnalysisCLIError(
            f"cannot read trajectory NPZ: {array_path}"
        ) from error
    count = sum(len(starts) for starts in expected_by_episode.values())
    if (
        document.get("forecast_example_count") != count
        or tokens.shape != (count, PREFIX_ACTION_COUNT_V1, PREFIX_TOKEN_WIDTH_V1)
        or targets.shape != (count, FORECAST_TARGET_DIMENSION_V1)
        or episode_index.shape != (count,)
        or window_start.shape != (count,)
        or tokens.dtype != np.float32
        or targets.dtype != np.float32
        or episode_index.dtype != np.int64
        or window_start.dtype != np.int64
        or not np.all(np.isfinite(tokens))
        or not np.all(np.isfinite(targets))
    ):
        _fail("trajectory NPZ shape, dtype, count, or finiteness changed")
    expected_pairs = [
        (episode, start)
        for episode in range(16)
        for start in expected_by_episode[episode]
    ]
    observed_pairs = list(
        zip(episode_index.tolist(), window_start.tolist(), strict=True)
    )
    if observed_pairs != expected_pairs:
        _fail("trajectory NPZ windows differ from the exact spanning formula")
    replayed_tokens = np.asarray(
        [example.tokens for example in replayed_examples], dtype=np.float32
    )
    replayed_targets = np.asarray(
        [example.target for example in replayed_examples], dtype=np.float32
    )
    if (
        not np.array_equal(tokens, replayed_tokens)
        or not np.array_equal(targets, replayed_targets)
    ):
        _fail("trajectory NPZ differs from exact action/tape replay")
    examples: list[ForecastExampleV1] = []
    for index, (episode, start) in enumerate(expected_pairs):
        window_key = ForecastWindowKeyV1(
            player_id=key,
            tape_root=expected_root,
            episode_index=episode,
            window_start=start,
        )
        examples.append(
            ForecastExampleV1(
                key=window_key,
                tokens=tuple(
                    tuple(float(value) for value in row)
                    for row in tokens[index]
                ),
                target=tuple(float(value) for value in targets[index]),
                target_source_key=window_key,
            )
        )
    return tuple(examples), expected_root, len(summaries)


def _bare_encoder_bytes(encoder: Any) -> bytes:
    import torch

    state = {
        key: value.detach().cpu()
        for key, value in encoder.state_dict().items()
    }
    output = io.BytesIO()
    torch.save(state, output)
    return output.getvalue()


def _stage_receipt(
    receipt: Any,
    *,
    protocol: Mapping[str, Any],
    encoder_filename: str,
    trajectory_document_count: int,
    complete_episode_count: int,
    runtime_provenance: Mapping[str, str],
) -> dict[str, Any]:
    core = receipt.document()
    return {
        "schema": ENCODER_STAGE_RECEIPT_SCHEMA_V1,
        "protocol_id": protocol["protocol_id"],
        "source_commit": protocol["source_commit"],
        "pilot_execution_identity": protocol["pilot_execution_identity"],
        "target_mode": core["target_mode"],
        "initialization_seed": core["initialization_seed"],
        "trajectory_document_count": trajectory_document_count,
        "complete_trajectory_episode_count": complete_episode_count,
        "example_count": core["example_count"],
        "player_count": core["player_count"],
        "input_shape": core["input_shape"],
        "hidden_width": core["hidden_width"],
        "target_dimension": core["target_dimension"],
        "encoder_parameter_count": FORECAST_ENCODER_PARAMETER_COUNT_V1,
        "encoder_plus_linear_head_parameter_count": (
            FORECAST_MODEL_PARAMETER_COUNT_V1
        ),
        "optimizer": core["optimizer"],
        "learning_rate": core["learning_rate"],
        "batch_size": core["batch_size"],
        "fixed_epoch_count": core["fixed_epoch_count"],
        "training_loss_by_epoch": core["training_loss_by_epoch"],
        "device_name": core["device_name"],
        "encoder_frozen": core["encoder_frozen"],
        "forecast_head_discarded": core["forecast_head_discarded"],
        "skill_labels_opened_during_training": False,
        "encoder_state_filename": encoder_filename,
        "encoder_state_is_bare_gru_state_dict": True,
        "CUBLAS_WORKSPACE_CONFIG": ":4096:8",
        **runtime_provenance,
    }


def _run_fit_encoders(args: argparse.Namespace) -> dict[str, Any]:
    if os.environ.get("CUBLAS_WORKSPACE_CONFIG") != ":4096:8":
        _fail("deterministic cuBLAS workspace configuration changed")
    protocol_path = require_path_outside_repository_v1(
        repository=REPOSITORY, path=args.protocol, label="U002 protocol input"
    )
    manifest_path = require_path_outside_repository_v1(
        repository=REPOSITORY, path=args.manifest, label="U002 manifest input"
    )
    trajectory_dirs = [
        require_path_outside_repository_v1(
            repository=REPOSITORY, path=path, label="trajectory evidence directory"
        )
        for path in args.trajectory_dir
    ]
    output_dir = require_path_outside_repository_v1(
        repository=REPOSITORY, path=args.output_dir, label="encoder output directory"
    )
    protocol = _load_protocol(protocol_path)
    runtime_provenance = _analysis_runtime_provenance_v1(args, protocol)
    manifest = _load_manifest(manifest_path, protocol)
    _validate_analysis_runtime(manifest, requested_device=args.device)
    outputs = {
        "aligned_encoder": output_dir / ALIGNED_ENCODER_FILENAME_V1,
        "shuffled_encoder": output_dir / SHUFFLED_ENCODER_FILENAME_V1,
        "aligned_receipt": output_dir / ALIGNED_RECEIPT_FILENAME_V1,
        "shuffled_receipt": output_dir / SHUFFLED_RECEIPT_FILENAME_V1,
    }
    if any(path.exists() for path in outputs.values()):
        _fail("encoder-stage output already exists")
    examples: list[ForecastExampleV1] = []
    tape_roots: list[str] = []
    episode_count = 0
    train_jobs = [
        manifest["player_jobs"][key]
        for key in _expected_player_order()
        if manifest["player_jobs"][key]["split"] == "TRAIN"
    ]
    for job in train_jobs:
        metadata_path = _resolve_unique_file(
            trajectory_dirs,
            job["trajectory_metadata_filename"],
            label="trajectory metadata",
        )
        array_path = _resolve_unique_file(
            trajectory_dirs,
            job["trajectory_array_filename"],
            label="trajectory array",
        )
        player_examples, tape_root, player_episodes = (
            _trajectory_examples_from_artifacts(
                metadata_path,
                array_path,
                protocol=protocol,
                job=job,
            )
        )
        examples.extend(player_examples)
        tape_roots.append(tape_root)
        episode_count += player_episodes
    if (
        len(train_jobs) != EXPECTED_TRAJECTORY_PLAYER_ARTIFACT_COUNT_V1
        or set(tape_roots) != {protocol["trajectory_tape_root"]}
        or episode_count != EXPECTED_COMPLETE_TRAJECTORY_EPISODE_COUNT_V1
    ):
        _fail("encoder stage did not close 288 players and 4,608 episodes")
    train_keys = [job["player_key"] for job in train_jobs]
    test_keys = [
        key
        for key in _expected_player_order()
        if manifest["player_jobs"][key]["split"] == "TEST"
    ]
    trajectory_roots = (protocol["trajectory_tape_root"],)
    forbidden_roots = (
        protocol["label_tape_root"],
        protocol["probe_tape_root"],
    )
    aligned_rows = tuple(examples)
    shuffled_rows = player_shuffled_targets_v1(aligned_rows)
    initialization_seed = protocol["forecast_encoder_contract"][
        "initialization_seed"
    ]
    aligned_encoder, aligned_receipt = train_forecast_encoder_v1(
        aligned_rows,
        eligible_player_ids=train_keys,
        trajectory_tape_roots=trajectory_roots,
        target_mode=ALIGNED_TARGET_MODE_V1,
        initialization_seed=initialization_seed,
        device_name=args.device,
        ineligible_player_ids=test_keys,
        forbidden_tape_roots=forbidden_roots,
    )
    shuffled_encoder, shuffled_receipt = train_forecast_encoder_v1(
        shuffled_rows,
        eligible_player_ids=train_keys,
        trajectory_tape_roots=trajectory_roots,
        target_mode=PLAYER_SHUFFLED_TARGET_MODE_V1,
        initialization_seed=initialization_seed,
        device_name=args.device,
        ineligible_player_ids=test_keys,
        forbidden_tape_roots=forbidden_roots,
    )
    aligned_document = _stage_receipt(
        aligned_receipt,
        protocol=protocol,
        encoder_filename=ALIGNED_ENCODER_FILENAME_V1,
        trajectory_document_count=len(train_jobs),
        complete_episode_count=episode_count,
        runtime_provenance=runtime_provenance,
    )
    shuffled_document = _stage_receipt(
        shuffled_receipt,
        protocol=protocol,
        encoder_filename=SHUFFLED_ENCODER_FILENAME_V1,
        trajectory_document_count=len(train_jobs),
        complete_episode_count=episode_count,
        runtime_provenance=runtime_provenance,
    )
    write_exclusive_bytes_v1(
        outputs["aligned_encoder"], _bare_encoder_bytes(aligned_encoder)
    )
    write_exclusive_bytes_v1(
        outputs["shuffled_encoder"], _bare_encoder_bytes(shuffled_encoder)
    )
    write_exclusive_bytes_v1(
        outputs["aligned_receipt"], canonical_json_bytes(aligned_document)
    )
    write_exclusive_bytes_v1(
        outputs["shuffled_receipt"], canonical_json_bytes(shuffled_document)
    )
    return {
        "success": True,
        "stage": "FIT_ENCODERS",
        "protocol_id": protocol["protocol_id"],
        "trajectory_document_count": len(train_jobs),
        "complete_trajectory_episode_count": episode_count,
        "forecast_example_count": len(examples),
        "encoder_state_count": 2,
        "receipt_count": 2,
        "skill_label_path_argument_present": False,
        "outputs": {key: str(path) for key, path in outputs.items()},
        **runtime_provenance,
    }


def _load_frozen_encoder(path: Path, *, expected_name: str, device_name: str) -> Any:
    if path.name != expected_name or not path.is_file():
        _fail("frozen encoder path or basename changed")
    import torch

    device = torch.device(device_name)
    if device.type == "cuda" and not torch.cuda.is_available():
        _fail("requested analysis CUDA device is unavailable")
    state = torch.load(path, map_location=device, weights_only=True)
    encoder = forecast_model_factory_v1(torch)().encoder.to(device)
    if (
        not isinstance(state, Mapping)
        or set(state) != set(encoder.state_dict())
        or any(not torch.is_tensor(value) for value in state.values())
        or any(not bool(torch.isfinite(value).all()) for value in state.values())
    ):
        _fail("encoder PT is not one exact finite bare GRU state_dict")
    try:
        encoder.load_state_dict(state, strict=True)
    except RuntimeError as error:
        raise LearnedResourceForecastAnalysisCLIError(
            "encoder PT tensor shapes changed"
        ) from error
    encoder.eval()
    for parameter in encoder.parameters():
        parameter.requires_grad_(False)
    return encoder


def _probe_traces_from_document(
    path: Path,
    *,
    protocol: Mapping[str, Any],
    job: Mapping[str, Any],
) -> tuple[tuple[PolicyTraceV1, ...], str]:
    document = _read_json(path, label="eight-action probe evidence")
    key = job["player_key"]
    _validate_player_evidence_ownership(
        document, protocol=protocol, job=job
    )
    root = protocol["probe_tape_root"]
    rows = document.get("probe_rows")
    if (
        document.get("schema") != PROBE_EVIDENCE_SCHEMA_V1
        or document.get("protocol_id") != protocol["protocol_id"]
        or document.get("source_commit") != protocol["source_commit"]
        or document.get("pilot_execution_identity")
        != protocol["pilot_execution_identity"]
        or document.get("lane") != "EIGHT_ACTION_NATURAL_OPENING_PROBE"
        or document.get("player_identity", {}).get("player_key") != key
        or document.get("probe_tape_root") != root
        or document.get("probe_count") != PROBES_PER_PLAYER_V1
        or document.get("exact_accepted_actions_per_probe")
        != PREFIX_ACTION_COUNT_V1
        or document.get("skill_label_or_complete_outcome_included") is not False
        or type(rows) is not list
        or len(rows) != PROBES_PER_PLAYER_V1
        or document.get("artifact_manifest", {}).get("filename") != path.name
        or document.get("artifact_manifest", {}).get(
            "contains_other_lane_content"
        )
        is not False
    ):
        _fail("probe document differs from its frozen lane identity")
    traces: list[PolicyTraceV1] = []
    for episode_index, row in enumerate(rows):
        if type(row) is not dict or row.get("episode_index") != episode_index:
            _fail("probe row episode identity changed")
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
            or row.get("exact_accepted_action_count") != 8
            or row.get("later_state_or_episode_outcome_included") is not False
        ):
            _fail("probe row is not exactly states s0..s8 and actions a0..a7")
        try:
            states = tuple(
                standard_2048.state_from_board_v1(tuple(board)) for board in boards
            )
            if states[0] != initial_state_v1(
                seed=root, episode_index=episode_index
            ):
                _fail("probe initial board differs from the registered tape")
            for decision_index, action_index in enumerate(actions):
                replay = transition_v1(
                    states[decision_index],
                    action_index,
                    seed=root,
                    episode_index=episode_index,
                    decision_index=decision_index,
                )
                if (
                    replay.next_state != states[decision_index + 1]
                    or replay.merge_score != scores[decision_index]
                    or replay.tape_digest != digests[decision_index]
                ):
                    _fail(
                        "probe next state, merge score, or tape digest differs "
                        "from exact transition replay"
                    )
            trace = PolicyTraceV1(
                tape_root=root,
                episode_index=episode_index,
                states=states,
                action_indices=tuple(actions),
                merge_scores=tuple(scores),
                tape_digests=tuple(digests),
                completed_game=(
                    states[-1].status
                    is not standard_2048.Swipe2048Status.ACTIVE
                ),
            )
        except (TypeError, ValueError) as error:
            raise LearnedResourceForecastAnalysisCLIError(
                "probe row contains an invalid board or accepted action"
            ) from error
        if row.get("status_after_eight_actions") != states[-1].status.value:
            _fail("probe status differs from board-derived status")
        traces.append(trace)
    return tuple(traces), root


def _matrix_bytes(
    player_keys: Sequence[str],
    raw: np.ndarray,
    shuffled: np.ndarray,
    aligned: np.ndarray,
) -> bytes:
    output = io.BytesIO()
    np.savez_compressed(
        output,
        player_keys=np.asarray(player_keys, dtype=np.str_),
        raw_prefix=raw,
        raw_plus_player_shuffled_forecast=shuffled,
        raw_plus_aligned_resource_forecast=aligned,
    )
    return output.getvalue()


def _run_encode_probes(args: argparse.Namespace) -> dict[str, Any]:
    protocol_path = require_path_outside_repository_v1(
        repository=REPOSITORY, path=args.protocol, label="U002 protocol input"
    )
    manifest_path = require_path_outside_repository_v1(
        repository=REPOSITORY, path=args.manifest, label="U002 manifest input"
    )
    probe_dirs = [
        require_path_outside_repository_v1(
            repository=REPOSITORY, path=path, label="probe evidence directory"
        )
        for path in args.probe_dir
    ]
    aligned_path = require_path_outside_repository_v1(
        repository=REPOSITORY,
        path=args.aligned_encoder,
        label="aligned encoder input",
    )
    shuffled_path = require_path_outside_repository_v1(
        repository=REPOSITORY,
        path=args.shuffled_encoder,
        label="shuffled encoder input",
    )
    output_dir = require_path_outside_repository_v1(
        repository=REPOSITORY, path=args.output_dir, label="probe matrix output"
    )
    protocol = _load_protocol(protocol_path)
    runtime_provenance = _analysis_runtime_provenance_v1(args, protocol)
    manifest = _load_manifest(manifest_path, protocol)
    _validate_analysis_runtime(manifest, requested_device=args.device)
    matrix_path = output_dir / MATRIX_FILENAME_V1
    metadata_path = output_dir / MATRIX_METADATA_FILENAME_V1
    if matrix_path.exists() or metadata_path.exists():
        _fail("probe matrix-stage output already exists")
    aligned_encoder = _load_frozen_encoder(
        aligned_path,
        expected_name=ALIGNED_ENCODER_FILENAME_V1,
        device_name=args.device,
    )
    shuffled_encoder = _load_frozen_encoder(
        shuffled_path,
        expected_name=SHUFFLED_ENCODER_FILENAME_V1,
        device_name=args.device,
    )
    player_keys = _expected_player_order()
    raw_rows: list[list[tuple[float, ...]]] = []
    token_rows: list[tuple[tuple[float, ...], ...]] = []
    probe_roots: list[str] = []
    for key in player_keys:
        job = manifest["player_jobs"][key]
        probe_path = _resolve_unique_file(
            probe_dirs, job["probe_filename"], label="probe evidence"
        )
        traces, root = _probe_traces_from_document(
            probe_path, protocol=protocol, job=job
        )
        raw_rows.append([raw_prefix_v1(trace) for trace in traces])
        token_rows.extend(prefix_tokens_v1(trace) for trace in traces)
        probe_roots.append(root)
    if (
        len(player_keys) != EXPECTED_PLAYER_COUNT_V1
        or set(probe_roots) != {protocol["probe_tape_root"]}
        or len(token_rows) != EXPECTED_PROBE_RECORD_COUNT_V1
    ):
        _fail("probe stage did not close 432 players and 6,912 probes")
    aligned_embeddings = np.asarray(
        frozen_embeddings_v1(aligned_encoder, token_rows), dtype=np.float32
    ).reshape(EXPECTED_PLAYER_COUNT_V1, PROBES_PER_PLAYER_V1, FORECAST_HIDDEN_WIDTH_V1)
    shuffled_embeddings = np.asarray(
        frozen_embeddings_v1(shuffled_encoder, token_rows), dtype=np.float32
    ).reshape(
        EXPECTED_PLAYER_COUNT_V1,
        PROBES_PER_PLAYER_V1,
        FORECAST_HIDDEN_WIDTH_V1,
    )
    raw = np.asarray(raw_rows, dtype=np.float32)
    shuffled = np.concatenate((raw, shuffled_embeddings), axis=2)
    aligned = np.concatenate((raw, aligned_embeddings), axis=2)
    if (
        raw.shape
        != (
            EXPECTED_PLAYER_COUNT_V1,
            PROBES_PER_PLAYER_V1,
            RAW_PREFIX_DIMENSION_V1,
        )
        or shuffled.shape
        != (EXPECTED_PLAYER_COUNT_V1, PROBES_PER_PLAYER_V1, LEARNED_PREFIX_DIMENSION_V1)
        or aligned.shape
        != (EXPECTED_PLAYER_COUNT_V1, PROBES_PER_PLAYER_V1, LEARNED_PREFIX_DIMENSION_V1)
        or not np.all(np.isfinite(raw))
        or not np.all(np.isfinite(shuffled))
        or not np.all(np.isfinite(aligned))
        or not np.array_equal(shuffled[:, :, :RAW_PREFIX_DIMENSION_V1], raw)
        or not np.array_equal(aligned[:, :, :RAW_PREFIX_DIMENSION_V1], raw)
    ):
        _fail("probe representation matrix shape, finiteness, or raw block changed")
    metadata = {
        "schema": PROBE_MATRIX_METADATA_SCHEMA_V1,
        "protocol_id": protocol["protocol_id"],
        "source_commit": protocol["source_commit"],
        "pilot_execution_identity": protocol["pilot_execution_identity"],
        "matrix_filename": MATRIX_FILENAME_V1,
        "player_keys": list(player_keys),
        "player_count": EXPECTED_PLAYER_COUNT_V1,
        "probe_document_count": EXPECTED_PLAYER_COUNT_V1,
        "probe_record_count": EXPECTED_PROBE_RECORD_COUNT_V1,
        "probe_tape_roots": [protocol["probe_tape_root"]],
        "representations": {
            RAW_PREFIX_ARM_V1: {
                "array_key": "raw_prefix",
                "shape": list(raw.shape),
                "dimension": RAW_PREFIX_DIMENSION_V1,
            },
            SHUFFLED_FORECAST_ARM_V1: {
                "array_key": "raw_plus_player_shuffled_forecast",
                "shape": list(shuffled.shape),
                "dimension": LEARNED_PREFIX_DIMENSION_V1,
            },
            ALIGNED_FORECAST_ARM_V1: {
                "array_key": "raw_plus_aligned_resource_forecast",
                "shape": list(aligned.shape),
                "dimension": LEARNED_PREFIX_DIMENSION_V1,
            },
        },
        "encoder_state_files": [
            ALIGNED_ENCODER_FILENAME_V1,
            SHUFFLED_ENCODER_FILENAME_V1,
        ],
        "encoder_state_count": 2,
        "learned_raw_prefix_blocks_equal_raw": True,
        "skill_label_path_argument_present": False,
        "skill_label_file_opened": False,
        "dtype": "float32",
        **runtime_provenance,
    }
    write_exclusive_bytes_v1(
        matrix_path, _matrix_bytes(player_keys, raw, shuffled, aligned)
    )
    write_exclusive_bytes_v1(metadata_path, canonical_json_bytes(metadata))
    return {
        "success": True,
        "stage": "ENCODE_PROBES",
        "protocol_id": protocol["protocol_id"],
        "player_count": EXPECTED_PLAYER_COUNT_V1,
        "probe_record_count": EXPECTED_PROBE_RECORD_COUNT_V1,
        "encoder_state_count": 2,
        "skill_label_path_argument_present": False,
        "matrix": str(matrix_path),
        "metadata": str(metadata_path),
        **runtime_provenance,
    }


def _load_matrix_bundle(
    matrix_path: Path,
    metadata_path: Path,
    *,
    protocol: Mapping[str, Any],
) -> tuple[dict[str, dict[str, np.ndarray]], dict[str, Any]]:
    metadata = _read_json(metadata_path, label="probe matrix metadata")
    player_keys = _expected_player_order()
    expected_representations = {
        RAW_PREFIX_ARM_V1: {
            "array_key": "raw_prefix",
            "shape": [EXPECTED_PLAYER_COUNT_V1, PROBES_PER_PLAYER_V1, 184],
            "dimension": RAW_PREFIX_DIMENSION_V1,
        },
        SHUFFLED_FORECAST_ARM_V1: {
            "array_key": "raw_plus_player_shuffled_forecast",
            "shape": [EXPECTED_PLAYER_COUNT_V1, PROBES_PER_PLAYER_V1, 248],
            "dimension": LEARNED_PREFIX_DIMENSION_V1,
        },
        ALIGNED_FORECAST_ARM_V1: {
            "array_key": "raw_plus_aligned_resource_forecast",
            "shape": [EXPECTED_PLAYER_COUNT_V1, PROBES_PER_PLAYER_V1, 248],
            "dimension": LEARNED_PREFIX_DIMENSION_V1,
        },
    }
    if (
        matrix_path.name != MATRIX_FILENAME_V1
        or metadata_path.name != MATRIX_METADATA_FILENAME_V1
        or metadata.get("schema") != PROBE_MATRIX_METADATA_SCHEMA_V1
        or metadata.get("protocol_id") != protocol["protocol_id"]
        or metadata.get("source_commit") != protocol["source_commit"]
        or metadata.get("pilot_execution_identity")
        != protocol["pilot_execution_identity"]
        or metadata.get("matrix_filename") != matrix_path.name
        or metadata.get("player_keys") != list(player_keys)
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
    ):
        _fail("probe matrix metadata identity, count, or lane boundary changed")
    try:
        with np.load(matrix_path, allow_pickle=False) as archive:
            if set(archive.files) != _NPZ_MATRIX_KEYS:
                _fail("probe matrix NPZ member registry changed")
            encoded_keys = np.asarray(archive["player_keys"])
            raw = np.asarray(archive["raw_prefix"])
            shuffled = np.asarray(archive["raw_plus_player_shuffled_forecast"])
            aligned = np.asarray(archive["raw_plus_aligned_resource_forecast"])
    except (OSError, ValueError) as error:
        raise LearnedResourceForecastAnalysisCLIError(
            f"cannot read probe matrix NPZ: {matrix_path}"
        ) from error
    if (
        encoded_keys.tolist() != list(player_keys)
        or raw.shape != (EXPECTED_PLAYER_COUNT_V1, 16, RAW_PREFIX_DIMENSION_V1)
        or shuffled.shape != (EXPECTED_PLAYER_COUNT_V1, 16, LEARNED_PREFIX_DIMENSION_V1)
        or aligned.shape != (EXPECTED_PLAYER_COUNT_V1, 16, LEARNED_PREFIX_DIMENSION_V1)
        or raw.dtype != np.float32
        or shuffled.dtype != np.float32
        or aligned.dtype != np.float32
        or not np.all(np.isfinite(raw))
        or not np.all(np.isfinite(shuffled))
        or not np.all(np.isfinite(aligned))
        or not np.array_equal(shuffled[:, :, :RAW_PREFIX_DIMENSION_V1], raw)
        or not np.array_equal(aligned[:, :, :RAW_PREFIX_DIMENSION_V1], raw)
    ):
        _fail("probe matrix arrays changed identity, shape, dtype, or raw block")
    arrays = {
        RAW_PREFIX_ARM_V1: raw,
        SHUFFLED_FORECAST_ARM_V1: shuffled,
        ALIGNED_FORECAST_ARM_V1: aligned,
    }
    nested = {
        representation: {
            key: arrays[representation][index]
            for index, key in enumerate(player_keys)
        }
        for representation in arrays
    }
    return nested, metadata


def _load_encoder_receipts(
    directory: Path, *, protocol: Mapping[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    documents = []
    expected = (
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
    )
    for filename, mode, state_filename in expected:
        document = _read_json(directory / filename, label="encoder receipt")
        if (
            not (directory / state_filename).is_file()
            or (directory / state_filename).name != state_filename
            or document.get("schema") != ENCODER_STAGE_RECEIPT_SCHEMA_V1
            or document.get("protocol_id") != protocol["protocol_id"]
            or document.get("source_commit") != protocol["source_commit"]
            or document.get("target_mode") != mode
            or document.get("initialization_seed")
            != protocol["forecast_encoder_contract"]["initialization_seed"]
            or document.get("trajectory_document_count")
            != EXPECTED_TRAJECTORY_PLAYER_ARTIFACT_COUNT_V1
            or document.get("complete_trajectory_episode_count")
            != EXPECTED_COMPLETE_TRAJECTORY_EPISODE_COUNT_V1
            or document.get("player_count")
            != EXPECTED_TRAJECTORY_PLAYER_ARTIFACT_COUNT_V1
            or document.get("encoder_parameter_count")
            != FORECAST_ENCODER_PARAMETER_COUNT_V1
            or document.get("encoder_plus_linear_head_parameter_count")
            != FORECAST_MODEL_PARAMETER_COUNT_V1
            or document.get("fixed_epoch_count") != 50
            or type(document.get("training_loss_by_epoch")) is not list
            or len(document["training_loss_by_epoch"]) != 50
            or document.get("encoder_frozen") is not True
            or document.get("forecast_head_discarded") is not True
            or document.get("skill_labels_opened_during_training") is not False
            or document.get("encoder_state_filename") != state_filename
            or document.get("encoder_state_is_bare_gru_state_dict") is not True
            or document.get("CUBLAS_WORKSPACE_CONFIG") != ":4096:8"
        ):
            _fail("encoder receipt differs from frozen fit-stage evidence")
        documents.append(document)
    if documents[0]["example_count"] != documents[1]["example_count"]:
        _fail("aligned and shuffled receipts changed training example support")
    return documents[0], documents[1]


def _status_counts(
    status_dirs: Sequence[Path], manifest: Mapping[str, Any]
) -> dict[str, int]:
    def validate_stream(basename: str, roster: Mapping[str, Any]) -> int:
        path = _resolve_unique_file(
            status_dirs, basename, label="worker status stream"
        )
        try:
            raw_lines = path.read_text(encoding="utf-8").splitlines()
        except OSError as error:
            raise LearnedResourceForecastAnalysisCLIError(
                f"cannot read status stream: {path}"
            ) from error
        rows: list[dict[str, Any]] = []
        for line in raw_lines:
            try:
                row = json.loads(line)
            except json.JSONDecodeError as error:
                raise LearnedResourceForecastAnalysisCLIError(
                    "status stream contains malformed JSONL"
                ) from error
            if type(row) is not dict:
                _fail("status stream row is not an object")
            rows.append(row)
        expected_ids = tuple(roster["execution_ids"])
        phase = roster["phase"]
        worker = roster["worker"]
        if (
            not rows
            or rows[0].get("event") != "WORKER_STARTED"
            or rows[-1].get("event") != "WORKER_COMPLETED"
            or sum(row.get("event") == "WORKER_STARTED" for row in rows) != 1
            or sum(row.get("event") == "WORKER_COMPLETED" for row in rows) != 1
            or any(
                row.get("event") in {"WORKER_FAILED", "JOB_FAILED"}
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
            or rows[-1].get("completed_job_count") != len(expected_ids)
        ):
            _fail("worker status lifecycle did not close exactly")
        started = [
            row for row in rows if row.get("event") == "JOB_STARTED"
        ]
        completed = [
            row for row in rows if row.get("event") == "JOB_COMPLETED"
        ]
        if (
            [row.get("execution_id") for row in started] != list(expected_ids)
            or [row.get("execution_id") for row in completed]
            != list(expected_ids)
            or [row.get("job_ordinal") for row in started]
            != list(range(len(expected_ids)))
            or [row.get("job_ordinal") for row in completed]
            != list(range(len(expected_ids)))
            or any(
                row.get("preexecution_identity_check_only") is not False
                for row in started
            )
            or any(
                row.get("completed_job_count") != index + 1
                or row.get("expected_job_count") != len(expected_ids)
                for index, row in enumerate(completed)
            )
        ):
            _fail("worker status job roster is missing, duplicated, or foreign")
        return len(completed)

    training_completed = sum(
        validate_stream(basename, roster)
        for basename, roster in manifest["training_stream_rosters"].items()
    )
    evidence_completed = sum(
        validate_stream(basename, roster)
        for basename, roster in manifest["evidence_stream_rosters"].items()
    )
    if (
        training_completed != EXPECTED_TRAINING_JOB_COUNT_V1
        or evidence_completed != EXPECTED_PLAYER_COUNT_V1
    ):
        _fail("twelve worker streams did not close the frozen job counts")
    return {
        "completed_training_jobs": training_completed,
        "failed_training_jobs": 0,
        "model_snapshots": EXPECTED_MODEL_SNAPSHOT_COUNT_V1,
        "completed_player_evidence_jobs": evidence_completed,
        "failed_player_evidence_jobs": 0,
        "missing_identities": 0,
        "duplicate_identities": 0,
        "foreign_identities": 0,
    }


def _training_artifact_counts(
    result_dirs: Sequence[Path],
    *,
    protocol: Mapping[str, Any],
    manifest: Mapping[str, Any],
) -> dict[str, int]:
    result_count = 0
    snapshot_count = 0
    for execution_id, job in manifest["training_jobs"].items():
        result_path = _resolve_unique_file(
            result_dirs,
            job["result_filename"],
            label="policy-training result",
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
        artifact_manifest = document.get("artifact_manifest")
        if (
            document.get("schema")
            != LEARNED_RESOURCE_POLICY_TRAINING_RESULT_SCHEMA_V1
            or document.get("protocol_id") != protocol["protocol_id"]
            or document.get("arm") != job["arm"]
            or document.get("seed") != job["seed"]
            or document.get("device") != job["device"]
            or document.get("execution_context", {}).get("execution_id")
            != execution_id
            or document.get("execution_context", {}).get("source_commit")
            != protocol["source_commit"]
            or document.get("execution_context", {}).get("hostname")
            != job["expected_hostname"]
            or document.get("execution_context", {}).get("device")
            != job["device"]
            or type(artifact_manifest) is not dict
            or artifact_manifest.get("result_filename") != result_path.name
            or artifact_manifest.get("checkpoint_files") != expected_rows
            or artifact_manifest.get("checkpoint_file_count") != 3
            or artifact_manifest.get("separate_final_model_artifact_written")
            is not False
        ):
            _fail("policy-training result identity or artifact roster changed")
        for filename in job["checkpoint_filenames"]:
            _resolve_unique_file(
                result_dirs, filename, label="policy snapshot"
            )
            snapshot_count += 1
        result_count += 1
    if (
        result_count != EXPECTED_TRAINING_JOB_COUNT_V1
        or snapshot_count != EXPECTED_MODEL_SNAPSHOT_COUNT_V1
    ):
        _fail("physical policy-training result and snapshot matrix is incomplete")
    return {
        "model_snapshots": snapshot_count,
    }


def _validate_worker_result_inventory(
    result_dirs: Sequence[Path], manifest: Mapping[str, Any]
) -> None:
    if len(result_dirs) != 6:
        _fail("worker result inventory requires exactly six directories")
    for worker_index, directory in enumerate(result_dirs):
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
            raise LearnedResourceForecastAnalysisCLIError(
                f"cannot scan worker result directory: {directory}"
            ) from error
        actual = {entry.name for entry in entries if entry.is_file()}
        if (
            any(not entry.is_file() for entry in entries)
            or len(actual) != len(entries)
            or actual != expected
        ):
            _fail(
                "worker result directory has missing, duplicate, foreign, or "
                "non-file artifacts"
            )


def _evidence_artifact_counts(
    result_dirs: Sequence[Path],
    *,
    protocol: Mapping[str, Any],
    manifest: Mapping[str, Any],
) -> dict[str, int]:
    trajectory_players = 0
    trajectory_episodes = 0
    probe_records = 0
    label_files = 0
    for key in _expected_player_order():
        job = manifest["player_jobs"][key]
        _resolve_unique_file(
            result_dirs, job["label_filename"], label="skill-label evidence"
        )
        label_files += 1
        probe_path = _resolve_unique_file(
            result_dirs, job["probe_filename"], label="probe evidence"
        )
        traces, _root = _probe_traces_from_document(
            probe_path, protocol=protocol, job=job
        )
        probe_records += len(traces)
        if job["split"] == "TRAIN":
            metadata_path = _resolve_unique_file(
                result_dirs,
                job["trajectory_metadata_filename"],
                label="trajectory metadata",
            )
            array_path = _resolve_unique_file(
                result_dirs,
                job["trajectory_array_filename"],
                label="trajectory array",
            )
            _examples, _root, episode_count = (
                _trajectory_examples_from_artifacts(
                    metadata_path,
                    array_path,
                    protocol=protocol,
                    job=job,
                )
            )
            trajectory_players += 1
            trajectory_episodes += episode_count
    if (
        trajectory_players != EXPECTED_TRAJECTORY_PLAYER_ARTIFACT_COUNT_V1
        or trajectory_episodes != EXPECTED_COMPLETE_TRAJECTORY_EPISODE_COUNT_V1
        or probe_records != EXPECTED_PROBE_RECORD_COUNT_V1
        or label_files != EXPECTED_PLAYER_COUNT_V1
    ):
        _fail("physical evidence artifact matrix is incomplete")
    return {
        "trajectory_player_artifacts": trajectory_players,
        "complete_trajectory_episodes": trajectory_episodes,
        "exact_eight_action_probe_records": probe_records,
    }


def _label_aggregates(
    label_dirs: Sequence[Path],
    *,
    protocol: Mapping[str, Any],
    manifest: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], list[str]]:
    aggregates = []
    roots = []
    for key in _expected_player_order():
        job = manifest["player_jobs"][key]
        path = _resolve_unique_file(
            label_dirs, job["label_filename"], label="skill-label evidence"
        )
        document = _read_json(path, label="skill-label evidence")
        _validate_player_evidence_ownership(
            document, protocol=protocol, job=job
        )
        root = protocol["label_tape_root"]
        score = document.get("skill_score")
        summaries = document.get("complete_episode_summaries")
        if (
            document.get("schema") != LABEL_EVIDENCE_SCHEMA_V1
            or document.get("protocol_id") != protocol["protocol_id"]
            or document.get("source_commit") != protocol["source_commit"]
            or document.get("pilot_execution_identity")
            != protocol["pilot_execution_identity"]
            or document.get("lane") != "INDEPENDENT_SKILL_LABEL"
            or document.get("player_identity", {}).get("player_key") != key
            or document.get("label_tape_root") != root
            or document.get("complete_episode_count") != 64
            or type(summaries) is not list
            or len(summaries) != 64
            or type(score) is not dict
            or score.get("kind") != "MEAN_TOTAL_MERGE_SCORE"
            or score.get("episode_count") != 64
            or document.get("skill_class_assigned") is not False
            or document.get("train_thresholds_read") is not False
            or document.get("artifact_manifest", {}).get("filename") != path.name
            or document.get("artifact_manifest", {}).get(
                "contains_other_lane_content"
            )
            is not False
        ):
            _fail("skill-label document differs from frozen lane identity")
        total = 0
        for episode_index, row in enumerate(summaries):
            if (
                type(row) is not dict
                or row.get("episode_index") != episode_index
                or row.get("goal_terminated_episode") is not True
                or row.get("continue_after_2048") is not False
                or row.get("terminal_status") not in {"WON", "LOST"}
                or type(row.get("total_merge_score")) is not int
                or row["total_merge_score"] < 0
            ):
                _fail("skill-label lane contains a non-complete episode")
            trace = _replay_complete_episode_summary(
                row, tape_root=root, episode_index=episode_index
            )
            total += trace.total_merge_score
        mean = total / 64
        if (
            score.get("total_merge_score_sum") != total
            or type(score.get("mean_total_merge_score")) not in {int, float}
            or not math.isfinite(float(score["mean_total_merge_score"]))
            or float(score["mean_total_merge_score"]) != mean
        ):
            _fail("skill-label aggregate does not replay from its 64 episodes")
        aggregates.append(
            {
                "base_seed": job["seed"],
                "generator_arm": job["arm"],
                "checkpoint": job["checkpoint"],
                "episode_count": 64,
                "mean_total_merge_score": float(mean),
            }
        )
        roots.append(root)
    if set(roots) != {protocol["label_tape_root"]}:
        _fail("skill-label documents do not share the registered matched root")
    return aggregates, roots


def _run_evaluate(args: argparse.Namespace) -> dict[str, Any]:
    protocol_path = require_path_outside_repository_v1(
        repository=REPOSITORY, path=args.protocol, label="U002 protocol input"
    )
    manifest_path = require_path_outside_repository_v1(
        repository=REPOSITORY, path=args.manifest, label="U002 manifest input"
    )
    status_dirs = [
        require_path_outside_repository_v1(
            repository=REPOSITORY, path=path, label="status directory"
        )
        for path in args.status_dir
    ]
    worker_result_dirs = [
        require_path_outside_repository_v1(
            repository=REPOSITORY,
            path=path,
            label="worker result directory",
        )
        for path in args.worker_result_dir
    ]
    if len(worker_result_dirs) != 6 or len(set(worker_result_dirs)) != 6:
        _fail("evaluate requires the six distinct worker result directories")
    matrix_path = require_path_outside_repository_v1(
        repository=REPOSITORY, path=args.matrix, label="probe matrix input"
    )
    matrix_metadata_path = require_path_outside_repository_v1(
        repository=REPOSITORY,
        path=args.matrix_metadata,
        label="probe matrix metadata input",
    )
    receipt_dir = require_path_outside_repository_v1(
        repository=REPOSITORY,
        path=args.encoder_receipt_dir,
        label="encoder receipt directory",
    )
    label_dirs = [
        require_path_outside_repository_v1(
            repository=REPOSITORY, path=path, label="skill-label directory"
        )
        for path in args.label_dir
    ]
    output = require_path_outside_repository_v1(
        repository=REPOSITORY, path=args.output, label="pilot result output"
    )
    if output.name != PILOT_RESULT_FILENAME_V1 or output.exists():
        _fail("pilot result must be a fresh path named pilot-result.json")

    # The order below is the scientific boundary: labels are resolved and
    # opened only after protocol, manifest, status, frozen receipts, and the
    # already-encoded probe matrix have all passed validation.
    protocol = _load_protocol(protocol_path)
    runtime_provenance = _analysis_runtime_provenance_v1(args, protocol)
    manifest = _load_manifest(manifest_path, protocol)
    _validate_analysis_runtime(manifest, requested_device=None)
    status = _status_counts(status_dirs, manifest)
    _validate_worker_result_inventory(worker_result_dirs, manifest)
    training_artifacts = _training_artifact_counts(
        worker_result_dirs, protocol=protocol, manifest=manifest
    )
    evidence_artifacts = _evidence_artifact_counts(
        worker_result_dirs, protocol=protocol, manifest=manifest
    )
    matrices, matrix_metadata = _load_matrix_bundle(
        matrix_path, matrix_metadata_path, protocol=protocol
    )
    _load_encoder_receipts(receipt_dir, protocol=protocol)
    aggregates, _label_roots = _label_aggregates(
        label_dirs, protocol=protocol, manifest=manifest
    )
    counts = status | training_artifacts | evidence_artifacts | {
        "forecast_encoder_receipts": 2,
        "frozen_encoder_states": sum(
            (receipt_dir / filename).is_file()
            for filename in (
                ALIGNED_ENCODER_FILENAME_V1,
                SHUFFLED_ENCODER_FILENAME_V1,
            )
        ),
        "label_aggregates": len(aggregates),
    }
    result = evaluate_learned_resource_forecast_pilot_v1(
        protocol, aggregates, matrices, counts
    )
    result = dict(result) | runtime_provenance
    write_exclusive_bytes_v1(output, canonical_json_bytes(result))
    return {
        "success": True,
        "stage": "EVALUATE",
        "protocol_id": protocol["protocol_id"],
        "result": str(output),
        "PROVISIONAL_DESIGN_SIGNAL_GATE": result[
            "PROVISIONAL_DESIGN_SIGNAL_GATE"
        ],
        "scientific_success": False,
        "scientific_success_claimed": False,
        "label_files_opened_only_in_final_stage": True,
        **runtime_provenance,
    }


def _run(args: argparse.Namespace) -> dict[str, Any]:
    if args.operation == "fit-encoders":
        return _run_fit_encoders(args)
    if args.operation == "encode-probes":
        return _run_encode_probes(args)
    if args.operation == "evaluate":
        return _run_evaluate(args)
    raise AssertionError("unknown U002 analysis operation")


def main(argv: Sequence[str] | None = None) -> int:
    try:
        summary = _run(_arguments(argv))
    except (
        LearnedResourceForecastAnalysisCLIError,
        LearnedResourceForecastEvaluatorV1Error,
        LearnedResourceForecastProtocolV1Error,
        ScienceExecutionIOV1Error,
    ) as error:
        raise SystemExit(str(error)) from error
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
