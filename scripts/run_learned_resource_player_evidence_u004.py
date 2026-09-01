#!/usr/bin/env python3
"""Collect one fresh U004 measurement from one read-only U002 snapshot."""

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
from acfqp.science.learned_resource_forecast_evidence_successor_protocol_v1 import (
    U002_PROTOCOL_ID_V1,
    U002_SOURCE_COMMIT_V1,
    LearnedResourceForecastEvidenceSuccessorProtocolV1Error,
    validate_ratified_learned_resource_forecast_evidence_successor_protocol_v1,
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
    expected_policy_training_execution_id_v1,
    policy_checkpoint_filename_v1,
)


REPOSITORY = Path(__file__).resolve().parents[1]


class LearnedResourcePlayerEvidenceSuccessorCLIError(RuntimeError):
    """One U004 measurement request, parent snapshot, or output is ineligible."""


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--predecessor-protocol", type=Path, required=True)
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
    parser.add_argument("--predecessor-training-execution-id", required=True)
    return parser.parse_args()


def _read_object(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise LearnedResourcePlayerEvidenceSuccessorCLIError(
            f"cannot read {label}: {path}"
        ) from error
    if type(value) is not dict:
        raise LearnedResourcePlayerEvidenceSuccessorCLIError(
            f"{label} must contain one JSON object"
        )
    return value


def _runtime_context(device_name: str) -> dict[str, Any]:
    import numpy as np
    import torch

    device = torch.device(device_name)
    if device.type == "cuda":
        if not torch.cuda.is_available():
            raise LearnedResourcePlayerEvidenceSuccessorCLIError(
                "requested CUDA player-evidence device is unavailable"
            )
        description: str | None = torch.cuda.get_device_name(device)
    else:
        description = None
    return {
        "hostname": socket.gethostname(),
        "python_version": ".".join(str(value) for value in sys.version_info[:3]),
        "numpy_version": np.__version__,
        "torch_version": str(torch.__version__),
        "torch_cuda_runtime_version": torch.version.cuda,
        "torch_cudnn_version": torch.backends.cudnn.version(),
        "device": str(device),
        "cuda_device_name": description,
    }


def _parent_snapshot_provenance(
    *, predecessor: dict[str, Any], training_execution_id: str
) -> dict[str, Any]:
    return {
        "predecessor_protocol_id": predecessor["protocol_id"],
        "predecessor_source_commit": predecessor["source_commit"],
        "predecessor_pilot_execution_identity": predecessor[
            "pilot_execution_identity"
        ],
        "predecessor_training_execution_id": training_execution_id,
        "snapshot_is_read_only_predecessor_input": True,
        "snapshot_is_u004_training_artifact": False,
    }


def _run(args: argparse.Namespace) -> dict[str, Any]:
    protocol_path = require_path_outside_repository_v1(
        repository=REPOSITORY, path=args.protocol, label="ratified U004 protocol"
    )
    predecessor_protocol_path = require_path_outside_repository_v1(
        repository=REPOSITORY,
        path=args.predecessor_protocol,
        label="ratified U002 predecessor protocol",
    )
    snapshot_path = require_path_outside_repository_v1(
        repository=REPOSITORY,
        path=args.snapshot,
        label="read-only U002 policy snapshot",
    )
    output_dir = require_path_outside_repository_v1(
        repository=REPOSITORY,
        path=args.output_dir,
        label="fresh U004 player-evidence directory",
    )
    source_commit = bound_clean_source_commit_v1(REPOSITORY)
    protocol = (
        validate_ratified_learned_resource_forecast_evidence_successor_protocol_v1(
            _read_object(protocol_path, "ratified U004 protocol")
        )
    )
    predecessor = validate_ratified_learned_resource_forecast_protocol_v1(
        _read_object(predecessor_protocol_path, "ratified U002 predecessor protocol")
    )
    if (
        protocol["source_commit"] != source_commit
        or predecessor["source_commit"] != U002_SOURCE_COMMIT_V1
        or predecessor["protocol_id"] != U002_PROTOCOL_ID_V1
        or protocol["predecessor_training_authority"]["protocol_id"]
        != predecessor["protocol_id"]
        or protocol["predecessor_training_authority"][
            "model_evaluation_tape_prefix"
        ]
        != predecessor["evaluation_tape_prefix"]
        or protocol["predecessor_training_authority"][
            "model_evaluation_reexecuted_in_u004"
        ]
        is not False
        or protocol["evaluation_tape_prefix"]
        != predecessor["evaluation_tape_prefix"]
    ):
        raise LearnedResourcePlayerEvidenceSuccessorCLIError(
            "U004 source or U002 predecessor protocol binding changed"
        )
    player_key_v1(args.seed, args.arm, args.checkpoint)
    if (
        args.arm not in protocol["arms"]
        or args.seed not in protocol["training_seeds"]
        or args.checkpoint not in protocol["training"]["evaluation_checkpoints"]
        or args.execution_id
        != expected_player_evidence_execution_id_v1(
            protocol,
            base_seed=args.seed,
            generator_arm=args.arm,
            checkpoint=args.checkpoint,
        )
        or args.predecessor_training_execution_id
        != expected_policy_training_execution_id_v1(
            predecessor, arm=args.arm, seed=args.seed
        )
    ):
        raise LearnedResourcePlayerEvidenceSuccessorCLIError(
            "successor player or predecessor training identity changed"
        )
    expected_snapshot_name = policy_checkpoint_filename_v1(
        arm=args.arm, seed=args.seed, checkpoint=args.checkpoint
    )
    if snapshot_path.name != expected_snapshot_name or not snapshot_path.is_file():
        raise LearnedResourcePlayerEvidenceSuccessorCLIError(
            "predecessor snapshot path or filename differs from player identity"
        )
    if type(args.device) is not str or not args.device or args.device.strip() != args.device:
        raise LearnedResourcePlayerEvidenceSuccessorCLIError(
            "player-evidence device must be one exact nonempty string"
        )
    if (
        protocol["self_supervised_trajectory_contract"]["episodes_per_player"]
        != TRAJECTORY_EPISODES_PER_TRAIN_PLAYER_V1
        or protocol["skill_label_contract"]["episodes_per_player"]
        != LABEL_EPISODES_PER_PLAYER_V1
        or protocol["probe_contract"]["probes_per_player"]
        != PROBES_PER_PLAYER_V1
    ):
        raise LearnedResourcePlayerEvidenceSuccessorCLIError(
            "U004 evidence-lane counts differ from U002 measurement logic"
        )
    names = player_evidence_artifact_basenames_v1(
        base_seed=args.seed,
        generator_arm=args.arm,
        checkpoint=args.checkpoint,
    )
    is_train = args.seed in LEARNED_RESOURCE_FORECAST_TRAIN_SEEDS_V1
    reserved = {name: output_dir / filename for name, filename in names.items()}
    output_paths = {
        "label_json": reserved["label_json"],
        "probe_json": reserved["probe_json"],
    }
    if is_train:
        output_paths.update(
            {
                "trajectory_json": reserved["trajectory_json"],
                "trajectory_npz": reserved["trajectory_npz"],
            }
        )
    if any(path.exists() for path in reserved.values()):
        raise LearnedResourcePlayerEvidenceSuccessorCLIError(
            "U004 player-evidence output already exists; identity is consumed"
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
        raise LearnedResourcePlayerEvidenceSuccessorCLIError(
            "evidence collector returned wrong train/test lane roster"
        )
    provenance = _parent_snapshot_provenance(
        predecessor=predecessor,
        training_execution_id=args.predecessor_training_execution_id,
    )

    def finalized(document: dict[str, Any], manifest: dict[str, Any]) -> dict[str, Any]:
        result = dict(document)
        snapshot = dict(result["policy_snapshot"])
        snapshot.update(provenance)
        result["policy_snapshot"] = snapshot
        result["artifact_manifest"] = manifest
        return result

    label = finalized(
        artifacts.label_document,
        {
            "lane": "INDEPENDENT_SKILL_LABEL",
            "filename": names["label_json"],
            "contains_other_lane_content": False,
        },
    )
    probe = finalized(
        artifacts.probe_document,
        {
            "lane": "EIGHT_ACTION_NATURAL_OPENING_PROBE",
            "filename": names["probe_json"],
            "contains_other_lane_content": False,
        },
    )
    if (
        label.get("schema") != LABEL_EVIDENCE_SCHEMA_V1
        or probe.get("schema") != PROBE_EVIDENCE_SCHEMA_V1
    ):
        raise LearnedResourcePlayerEvidenceSuccessorCLIError(
            "evidence collector returned foreign lane schemas"
        )
    if is_train:
        if artifacts.trajectory_document is None:
            raise AssertionError("train player lost trajectory document")
        trajectory = finalized(
            artifacts.trajectory_document,
            {
                "lane": "SELF_SUPERVISED_TRAJECTORY",
                "metadata_filename": names["trajectory_json"],
                "compressed_array_filename": names["trajectory_npz"],
                "contains_other_lane_content": False,
            },
        )
        if trajectory.get("schema") != TRAJECTORY_EVIDENCE_SCHEMA_V1:
            raise LearnedResourcePlayerEvidenceSuccessorCLIError(
                "trajectory collector returned foreign lane schema"
            )
        write_exclusive_bytes_v1(
            output_paths["trajectory_npz"],
            forecast_examples_npz_bytes_v1(artifacts.trajectory_examples),
        )
        write_exclusive_bytes_v1(
            output_paths["trajectory_json"], canonical_json_bytes(trajectory)
        )
    write_exclusive_bytes_v1(output_paths["probe_json"], canonical_json_bytes(probe))
    write_exclusive_bytes_v1(output_paths["label_json"], canonical_json_bytes(label))
    return {
        "success": True,
        "protocol_id": protocol["protocol_id"],
        "source_commit": source_commit,
        "predecessor_protocol_id": predecessor["protocol_id"],
        "predecessor_source_commit": predecessor["source_commit"],
        "predecessor_training_execution_id": args.predecessor_training_execution_id,
        "player_key": player_key_v1(args.seed, args.arm, args.checkpoint),
        "split": "TRAIN" if is_train else "TEST",
        "execution_id": args.execution_id,
        "artifact_paths": {
            name: str(path) for name, path in sorted(output_paths.items())
        },
        "artifact_count": len(output_paths),
        "trajectory_example_count": len(artifacts.trajectory_examples),
        "label_episode_count": label["complete_episode_count"],
        "probe_count": probe["probe_count"],
        "policy_snapshot_input_is_read_only_u002": True,
        "scientific_success_claimed": False,
    }


def main() -> int:
    try:
        summary = _run(_arguments())
    except (
        LearnedResourcePlayerEvidenceSuccessorCLIError,
        LearnedResourceForecastEvidenceV1Error,
        LearnedResourceForecastEvidenceSuccessorProtocolV1Error,
        LearnedResourceForecastProtocolV1Error,
        ScienceExecutionIOV1Error,
    ) as error:
        raise SystemExit(str(error)) from error
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
