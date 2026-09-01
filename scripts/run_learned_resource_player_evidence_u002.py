#!/usr/bin/env python3
"""Collect one registered U002 policy player's separated evidence lanes."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import socket
import sys
from typing import Any

from acfqp.phase3e_ids import canonical_json_bytes
from acfqp.science.execution_io_v1 import (
    ScienceExecutionIOV1Error,
    bound_clean_source_commit_v1,
    require_path_outside_repository_v1,
    write_exclusive_bytes_v1,
)
from acfqp.science.learned_resource_forecast_evidence_v1 import (
    LABEL_EVIDENCE_SCHEMA_V1,
    PROBE_EVIDENCE_SCHEMA_V1,
    TRAJECTORY_EVIDENCE_SCHEMA_V1,
    LearnedResourceForecastEvidenceV1Error,
    collect_registered_player_evidence_v1,
    expected_player_evidence_execution_id_v1,
    forecast_examples_npz_bytes_v1,
    player_evidence_artifact_basenames_v1,
)
from acfqp.science.learned_resource_forecast_protocol_v1 import (
    LABEL_EPISODES_PER_PLAYER_V1,
    LEARNED_RESOURCE_FORECAST_ARMS_V1,
    LEARNED_RESOURCE_FORECAST_CHECKPOINTS_V1,
    LEARNED_RESOURCE_FORECAST_TRAIN_SEEDS_V1,
    PROBES_PER_PLAYER_V1,
    TRAJECTORY_EPISODES_PER_TRAIN_PLAYER_V1,
    LearnedResourceForecastProtocolV1Error,
    player_key_v1,
    validate_ratified_learned_resource_forecast_protocol_v1,
)
from acfqp.science.matched_double_dqn_2048_learned_resource_pilot_v1 import (
    policy_checkpoint_filename_v1,
)


REPOSITORY = Path(__file__).resolve().parents[1]


class LearnedResourcePlayerEvidenceCLIError(RuntimeError):
    """One formal player-evidence CLI request or output is ineligible."""


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--arm", choices=LEARNED_RESOURCE_FORECAST_ARMS_V1, required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument(
        "--checkpoint",
        type=int,
        choices=LEARNED_RESOURCE_FORECAST_CHECKPOINTS_V1,
        required=True,
    )
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--execution-id", required=True)
    return parser.parse_args()


def _load_protocol(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise LearnedResourcePlayerEvidenceCLIError(
            f"cannot read ratified U002 protocol: {path}"
        ) from error
    if type(value) is not dict:
        raise LearnedResourcePlayerEvidenceCLIError(
            "ratified U002 protocol must contain one JSON object"
        )
    return validate_ratified_learned_resource_forecast_protocol_v1(value)


def _validate_execution_request(
    *,
    protocol: dict[str, Any],
    source_commit: str,
    snapshot: Path,
    arm: str,
    seed: int,
    checkpoint: int,
    device: str,
    execution_id: str,
) -> None:
    if protocol.get("source_commit") != source_commit:
        raise LearnedResourcePlayerEvidenceCLIError(
            "ratified U002 protocol source commit differs from runtime checkout"
        )
    player_key_v1(seed, arm, checkpoint)
    if (
        arm not in protocol["arms"]
        or seed not in protocol["training_seeds"]
        or checkpoint not in protocol["training"]["evaluation_checkpoints"]
    ):
        raise LearnedResourcePlayerEvidenceCLIError(
            "player identity is not registered by the ratified U002 protocol"
        )
    expected_execution_id = expected_player_evidence_execution_id_v1(
        protocol,
        base_seed=seed,
        generator_arm=arm,
        checkpoint=checkpoint,
    )
    if execution_id != expected_execution_id:
        raise LearnedResourcePlayerEvidenceCLIError(
            "execution ID differs from the registered U002 player identity"
        )
    expected_snapshot_name = policy_checkpoint_filename_v1(
        arm=arm, seed=seed, checkpoint=checkpoint
    )
    if snapshot.name != expected_snapshot_name or not snapshot.is_file():
        raise LearnedResourcePlayerEvidenceCLIError(
            "policy snapshot path or filename differs from the player identity"
        )
    if type(device) is not str or not device or device.strip() != device:
        raise LearnedResourcePlayerEvidenceCLIError(
            "player-evidence device name must be one exact nonempty string"
        )
    if (
        protocol["self_supervised_trajectory_contract"]["episodes_per_player"]
        != TRAJECTORY_EPISODES_PER_TRAIN_PLAYER_V1
        or protocol["skill_label_contract"]["episodes_per_player"]
        != LABEL_EPISODES_PER_PLAYER_V1
        or protocol["probe_contract"]["probes_per_player"]
        != PROBES_PER_PLAYER_V1
        or protocol["probe_contract"]["accepted_action_count"] != 8
    ):
        raise LearnedResourcePlayerEvidenceCLIError(
            "ratified U002 evidence-lane counts changed"
        )


def _runtime_context(device_name: str) -> dict[str, Any]:
    import numpy as np
    import torch

    device = torch.device(device_name)
    if device.type == "cuda":
        if not torch.cuda.is_available():
            raise LearnedResourcePlayerEvidenceCLIError(
                "requested CUDA player-evidence device is unavailable"
            )
        device_description: str | None = torch.cuda.get_device_name(device)
    else:
        device_description = None
    return {
        "hostname": socket.gethostname(),
        "python_version": ".".join(str(value) for value in sys.version_info[:3]),
        "numpy_version": np.__version__,
        "torch_version": str(torch.__version__),
        "torch_cuda_runtime_version": torch.version.cuda,
        "torch_cudnn_version": torch.backends.cudnn.version(),
        "device": str(device),
        "cuda_device_name": device_description,
    }


def _run(args: argparse.Namespace) -> dict[str, Any]:
    protocol_path = require_path_outside_repository_v1(
        repository=REPOSITORY,
        path=args.protocol,
        label="ratified U002 protocol input",
    )
    snapshot_path = require_path_outside_repository_v1(
        repository=REPOSITORY,
        path=args.snapshot,
        label="U002 policy snapshot input",
    )
    output_dir = require_path_outside_repository_v1(
        repository=REPOSITORY,
        path=args.output_dir,
        label="U002 player-evidence result directory",
    )
    source_commit = bound_clean_source_commit_v1(REPOSITORY)
    protocol = _load_protocol(protocol_path)
    _validate_execution_request(
        protocol=protocol,
        source_commit=source_commit,
        snapshot=snapshot_path,
        arm=args.arm,
        seed=args.seed,
        checkpoint=args.checkpoint,
        device=args.device,
        execution_id=args.execution_id,
    )
    names = player_evidence_artifact_basenames_v1(
        base_seed=args.seed,
        generator_arm=args.arm,
        checkpoint=args.checkpoint,
    )
    is_train = args.seed in LEARNED_RESOURCE_FORECAST_TRAIN_SEEDS_V1
    reserved_paths = {
        name: output_dir / filename for name, filename in names.items()
    }
    output_paths: dict[str, Path] = {
        "label_json": reserved_paths["label_json"],
        "probe_json": reserved_paths["probe_json"],
    }
    if is_train:
        output_paths.update(
            {
                "trajectory_json": reserved_paths["trajectory_json"],
                "trajectory_npz": reserved_paths["trajectory_npz"],
            }
        )
    # A test player is forbidden to produce trajectory artifacts, but stale
    # same-stem trajectory files would still contaminate that identity.
    if any(path.exists() for path in reserved_paths.values()):
        raise LearnedResourcePlayerEvidenceCLIError(
            "U002 player-evidence output already exists; the identity is consumed"
        )
    context = {
        "execution_id": args.execution_id,
        "source_commit": source_commit,
        **_runtime_context(args.device),
    }
    artifacts = collect_registered_player_evidence_v1(
        protocol=protocol,
        snapshot_path=snapshot_path,
        base_seed=args.seed,
        generator_arm=args.arm,
        checkpoint=args.checkpoint,
        device_name=args.device,
        execution_context=context,
    )
    if artifacts.is_train_player is not is_train:
        raise LearnedResourcePlayerEvidenceCLIError(
            "player evidence runtime returned the wrong train/test lane roster"
        )
    if (
        artifacts.label_document.get("schema") != LABEL_EVIDENCE_SCHEMA_V1
        or artifacts.probe_document.get("schema") != PROBE_EVIDENCE_SCHEMA_V1
        or (
            is_train
            and (
                artifacts.trajectory_document is None
                or artifacts.trajectory_document.get("schema")
                != TRAJECTORY_EVIDENCE_SCHEMA_V1
            )
        )
    ):
        raise LearnedResourcePlayerEvidenceCLIError(
            "player evidence runtime returned a foreign lane schema"
        )

    label_document = dict(artifacts.label_document)
    label_document["artifact_manifest"] = {
        "lane": "INDEPENDENT_SKILL_LABEL",
        "filename": names["label_json"],
        "contains_other_lane_content": False,
    }
    probe_document = dict(artifacts.probe_document)
    probe_document["artifact_manifest"] = {
        "lane": "EIGHT_ACTION_NATURAL_OPENING_PROBE",
        "filename": names["probe_json"],
        "contains_other_lane_content": False,
    }
    trajectory_document: dict[str, Any] | None = None
    npz_raw: bytes | None = None
    if is_train:
        if artifacts.trajectory_document is None:
            raise AssertionError("train player lost its trajectory document")
        trajectory_document = dict(artifacts.trajectory_document)
        trajectory_document["artifact_manifest"] = {
            "lane": "SELF_SUPERVISED_TRAJECTORY",
            "metadata_filename": names["trajectory_json"],
            "compressed_array_filename": names["trajectory_npz"],
            "contains_other_lane_content": False,
        }
        npz_raw = forecast_examples_npz_bytes_v1(
            artifacts.trajectory_examples
        )

    # The NPZ is written before its trajectory metadata.  Probe and label are
    # separate terminal artifacts; no summary below copies their contents.
    if is_train:
        if trajectory_document is None or npz_raw is None:
            raise AssertionError("train trajectory serialization disappeared")
        write_exclusive_bytes_v1(output_paths["trajectory_npz"], npz_raw)
        write_exclusive_bytes_v1(
            output_paths["trajectory_json"],
            canonical_json_bytes(trajectory_document),
        )
    write_exclusive_bytes_v1(
        output_paths["probe_json"], canonical_json_bytes(probe_document)
    )
    write_exclusive_bytes_v1(
        output_paths["label_json"], canonical_json_bytes(label_document)
    )

    return {
        "success": True,
        "protocol_id": protocol["protocol_id"],
        "source_commit": source_commit,
        "player_key": player_key_v1(args.seed, args.arm, args.checkpoint),
        "split": "TRAIN" if is_train else "TEST",
        "execution_id": args.execution_id,
        "artifact_paths": {
            name: str(path) for name, path in sorted(output_paths.items())
        },
        "artifact_count": len(output_paths),
        "trajectory_example_count": len(artifacts.trajectory_examples),
        "label_episode_count": artifacts.label_document["complete_episode_count"],
        "probe_count": artifacts.probe_document["probe_count"],
        "label_content_in_summary": False,
        "scientific_success_claimed": False,
    }


def main() -> int:
    try:
        summary = _run(_arguments())
    except (
        LearnedResourcePlayerEvidenceCLIError,
        LearnedResourceForecastEvidenceV1Error,
        LearnedResourceForecastProtocolV1Error,
        ScienceExecutionIOV1Error,
    ) as error:
        raise SystemExit(str(error)) from error
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
