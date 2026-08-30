#!/usr/bin/env python3
"""Run one seed-arm from an externally ratified hybrid confirmation."""

from __future__ import annotations

import argparse
import io
import json
from pathlib import Path
import platform
import socket
import sys

from acfqp.science.execution_io_v1 import (
    ScienceExecutionIOV1Error,
    bound_clean_source_commit_v1,
    require_path_outside_repository_v1,
    write_exclusive_bytes_v1,
)
from acfqp.science.latent_resource_hybrid_confirmatory_protocol_v1 import (
    HYBRID_CONFIRMATORY_ARMS_V1,
    LatentResourceHybridConfirmatoryProtocolV1Error,
    registered_hybrid_confirmatory_device_v1,
    validate_ratified_hybrid_confirmatory_protocol_v1,
)
from acfqp.science.matched_double_dqn_2048_hybrid_confirmatory_v1 import (
    HYBRID_CONFIRMATORY_RESULT_SCHEMA_V1,
    run_hybrid_confirmatory_seed_arm_v1,
)


REPOSITORY = Path(__file__).resolve().parents[1]


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--arm", choices=HYBRID_CONFIRMATORY_ARMS_V1, required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--execution-id", required=True)
    return parser.parse_args()


def _load_protocol(path: Path) -> dict:
    document = json.loads(path.read_text(encoding="utf-8"))
    if type(document) is not dict:
        raise LatentResourceHybridConfirmatoryProtocolV1Error(
            "ratified hybrid protocol must be a plain object"
        )
    return validate_ratified_hybrid_confirmatory_protocol_v1(document)


def _validate_execution_request(
    *, protocol: dict, source_commit: str, arm: str, seed: int, device: str
) -> None:
    training = protocol["training"]
    if protocol["source_commit"] != source_commit:
        raise LatentResourceHybridConfirmatoryProtocolV1Error(
            "ratified hybrid protocol source commit differs from runtime checkout"
        )
    if arm not in protocol["arms"] or seed not in protocol["training_seeds"]:
        raise LatentResourceHybridConfirmatoryProtocolV1Error(
            "seed-arm is not registered by the ratified hybrid protocol"
        )
    if (
        training["environment_steps_per_seed_arm"] != 100_000
        or training["evaluation_checkpoints"] != [25_000, 50_000, 100_000]
        or training["evaluation_episodes_per_checkpoint"] != 64
        or training["epsilon_schedule"]["decay_steps"] != 100_000
    ):
        raise LatentResourceHybridConfirmatoryProtocolV1Error(
            "ratified hybrid confirmatory schedule changed"
        )
    if (
        type(device) is not str
        or device != registered_hybrid_confirmatory_device_v1(seed)
    ):
        raise LatentResourceHybridConfirmatoryProtocolV1Error(
            "official hybrid execution requires the seed-paired CUDA device block"
        )


def main() -> int:
    args = _arguments()
    if not args.execution_id.strip():
        raise SystemExit("execution ID must be nonempty")
    try:
        protocol_path = require_path_outside_repository_v1(
            repository=REPOSITORY,
            path=args.protocol,
            label="ratified hybrid protocol input",
        )
        output_dir = require_path_outside_repository_v1(
            repository=REPOSITORY,
            path=args.output_dir,
            label="hybrid confirmatory result directory",
        )
        source_commit = bound_clean_source_commit_v1(REPOSITORY)
        protocol = _load_protocol(protocol_path)
        _validate_execution_request(
            protocol=protocol,
            source_commit=source_commit,
            arm=args.arm,
            seed=args.seed,
            device=args.device,
        )
    except (
        ScienceExecutionIOV1Error,
        LatentResourceHybridConfirmatoryProtocolV1Error,
    ) as error:
        raise SystemExit(str(error)) from error

    output_dir.mkdir(parents=True, exist_ok=True)
    stem = f"{args.arm.lower()}-seed-{args.seed}"
    result_path = output_dir / f"{stem}.json"
    model_path = output_dir / f"{stem}.pt"
    if result_path.exists() or model_path.exists():
        raise SystemExit(
            "hybrid confirmatory output already exists; use a fresh identity"
        )

    result, model = run_hybrid_confirmatory_seed_arm_v1(
        protocol=protocol,
        arm=args.arm,
        seed=args.seed,
        device_name=args.device,
    )
    if result.get("schema") != HYBRID_CONFIRMATORY_RESULT_SCHEMA_V1:
        raise RuntimeError("hybrid confirmatory runtime returned a foreign schema")

    import numpy as np
    import torch

    result["execution_context"] = {
        "execution_id": args.execution_id,
        "source_commit": source_commit,
        "hostname": socket.gethostname(),
        "python_version": platform.python_version(),
        "numpy_version": np.__version__,
        "torch_version": torch.__version__,
        "torch_cuda_runtime_version": torch.version.cuda,
        "torch_cudnn_version": torch.backends.cudnn.version(),
        "cuda_device_name": torch.cuda.get_device_name(torch.device(args.device)),
    }

    model_buffer = io.BytesIO()
    torch.save(model.state_dict(), model_buffer)
    write_exclusive_bytes_v1(model_path, model_buffer.getvalue())
    write_exclusive_bytes_v1(
        result_path,
        json.dumps(
            result,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8"),
    )
    print(
        json.dumps(
            {
                "success": True,
                "protocol_id": protocol["protocol_id"],
                "source_commit": source_commit,
                "arm": args.arm,
                "seed": args.seed,
                "execution_id": args.execution_id,
                "result": str(result_path),
                "model": str(model_path),
                "hybrid_confirmatory_joint_gate": result[
                    "hybrid_confirmatory_joint_gate"
                ],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
