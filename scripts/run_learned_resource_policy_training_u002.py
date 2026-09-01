#!/usr/bin/env python3
"""Run one fresh seed-arm policy-training job for U002."""

from __future__ import annotations

import argparse
import io
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
from acfqp.science.learned_resource_forecast_protocol_v1 import (
    LEARNED_RESOURCE_FORECAST_ARMS_V1,
    LearnedResourceForecastProtocolV1Error,
    validate_ratified_learned_resource_forecast_protocol_v1,
)
from acfqp.science.matched_double_dqn_2048_learned_resource_pilot_v1 import (
    LEARNED_RESOURCE_POLICY_TRAINING_RESULT_SCHEMA_V1,
    expected_policy_training_execution_id_v1,
    policy_checkpoint_filename_v1,
    run_learned_resource_policy_training_seed_arm_v1,
)


REPOSITORY = Path(__file__).resolve().parents[1]


class LearnedResourcePolicyTrainingCLIError(RuntimeError):
    """The U002 execution request or runtime output is ineligible."""


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument(
        "--arm", choices=LEARNED_RESOURCE_FORECAST_ARMS_V1, required=True
    )
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--execution-id", required=True)
    return parser.parse_args()


def _load_protocol(path: Path) -> dict[str, Any]:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise LearnedResourcePolicyTrainingCLIError(
            f"cannot read ratified U002 protocol: {path}"
        ) from error
    if type(document) is not dict:
        raise LearnedResourcePolicyTrainingCLIError(
            "ratified U002 protocol must contain one JSON object"
        )
    return validate_ratified_learned_resource_forecast_protocol_v1(document)


def _validate_execution_request(
    *,
    protocol: dict[str, Any],
    source_commit: str,
    arm: str,
    seed: int,
    device: str,
    execution_id: str,
) -> None:
    if protocol["source_commit"] != source_commit:
        raise LearnedResourcePolicyTrainingCLIError(
            "ratified U002 protocol source commit differs from runtime checkout"
        )
    if arm not in protocol["arms"] or seed not in protocol["training_seeds"]:
        raise LearnedResourcePolicyTrainingCLIError(
            "seed-arm is not registered by the ratified U002 protocol"
        )
    expected_execution_id = expected_policy_training_execution_id_v1(
        protocol, arm=arm, seed=seed
    )
    if execution_id != expected_execution_id:
        raise LearnedResourcePolicyTrainingCLIError(
            "execution ID differs from the registered U002 seed-arm identity"
        )
    if type(device) is not str or not device or device.strip() != device:
        raise LearnedResourcePolicyTrainingCLIError(
            "policy-training device name must be one exact nonempty string"
        )
    training = protocol["training"]
    if (
        training["environment_steps_per_seed_arm"] != 100_000
        or training["evaluation_checkpoints"] != [25_000, 50_000, 100_000]
        or training["evaluation_episodes_per_checkpoint"] != 64
        or training["epsilon_schedule"]["decay_steps"] != 100_000
        or training["save_inference_only_online_network_at_each_checkpoint"]
        is not True
    ):
        raise LearnedResourcePolicyTrainingCLIError(
            "ratified U002 policy-training and snapshot schedule changed"
        )


def _runtime_context(device_name: str) -> dict[str, Any]:
    import numpy as np
    import torch

    device = torch.device(device_name)
    if device.type == "cuda":
        if not torch.cuda.is_available():
            raise LearnedResourcePolicyTrainingCLIError(
                "requested CUDA policy-training device is unavailable"
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
    output_dir = require_path_outside_repository_v1(
        repository=REPOSITORY,
        path=args.output_dir,
        label="U002 policy-training result directory",
    )
    source_commit = bound_clean_source_commit_v1(REPOSITORY)
    protocol = _load_protocol(protocol_path)
    _validate_execution_request(
        protocol=protocol,
        source_commit=source_commit,
        arm=args.arm,
        seed=args.seed,
        device=args.device,
        execution_id=args.execution_id,
    )

    result_filename = f"{args.arm.lower()}-seed-{args.seed}.json"
    result_path = output_dir / result_filename
    checkpoint_rows = [
        {
            "checkpoint_environment_interactions": checkpoint,
            "filename": policy_checkpoint_filename_v1(
                arm=args.arm, seed=args.seed, checkpoint=checkpoint
            ),
            "artifact_kind": "INFERENCE_ONLY_BARE_ONLINE_STATE_DICT",
        }
        for checkpoint in protocol["training"]["evaluation_checkpoints"]
    ]
    artifact_paths = [
        result_path,
        *(output_dir / row["filename"] for row in checkpoint_rows),
    ]
    if any(path.exists() for path in artifact_paths):
        raise LearnedResourcePolicyTrainingCLIError(
            "U002 policy-training output already exists; the identity is consumed"
        )

    result, snapshots = run_learned_resource_policy_training_seed_arm_v1(
        protocol=protocol,
        arm=args.arm,
        seed=args.seed,
        device_name=args.device,
    )
    if result.get("schema") != LEARNED_RESOURCE_POLICY_TRAINING_RESULT_SCHEMA_V1:
        raise LearnedResourcePolicyTrainingCLIError(
            "U002 policy-training runtime returned a foreign result schema"
        )
    if tuple(snapshots) != tuple(
        protocol["training"]["evaluation_checkpoints"]
    ):
        raise LearnedResourcePolicyTrainingCLIError(
            "U002 policy-training runtime returned an incomplete snapshot roster"
        )

    result["execution_context"] = {
        "execution_id": args.execution_id,
        "source_commit": source_commit,
        **_runtime_context(args.device),
    }
    result["artifact_manifest"] = {
        "result_filename": result_filename,
        "checkpoint_files": checkpoint_rows,
        "checkpoint_file_count": len(checkpoint_rows),
        "separate_final_model_artifact_written": False,
    }

    import torch

    for row in checkpoint_rows:
        checkpoint = row["checkpoint_environment_interactions"]
        buffer = io.BytesIO()
        torch.save(snapshots[checkpoint], buffer)
        write_exclusive_bytes_v1(
            output_dir / row["filename"], buffer.getvalue()
        )
    write_exclusive_bytes_v1(result_path, canonical_json_bytes(result))
    return {
        "success": True,
        "protocol_id": protocol["protocol_id"],
        "source_commit": source_commit,
        "arm": args.arm,
        "seed": args.seed,
        "execution_id": args.execution_id,
        "result": str(result_path),
        "checkpoint_files": [
            str(output_dir / row["filename"]) for row in checkpoint_rows
        ],
        "checkpoint_file_count": len(checkpoint_rows),
        "separate_final_model_artifact_written": False,
        "policy_training_matrix_gate": result["policy_training_matrix_gate"],
    }


def main() -> int:
    try:
        summary = _run(_arguments())
    except (
        LearnedResourcePolicyTrainingCLIError,
        LearnedResourceForecastProtocolV1Error,
        ScienceExecutionIOV1Error,
    ) as error:
        raise SystemExit(str(error)) from error
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
