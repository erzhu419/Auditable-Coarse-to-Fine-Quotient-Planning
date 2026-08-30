#!/usr/bin/env python3
"""Run one seed-arm from the raw-preserving hybrid pilot."""

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
from acfqp.science.latent_resource_hybrid_protocol_v1 import (
    HYBRID_PILOT_ARMS,
    build_hybrid_pilot_protocol_v1,
)
from acfqp.science.matched_double_dqn_2048_hybrid_v1 import (
    HYBRID_PILOT_RESULT_SCHEMA_V1,
    run_hybrid_pilot_seed_arm_v1,
)


REPOSITORY = Path(__file__).resolve().parents[1]


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--arm", choices=HYBRID_PILOT_ARMS, required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--execution-id", required=True)
    return parser.parse_args()


def main() -> int:
    args = _arguments()
    protocol = build_hybrid_pilot_protocol_v1()
    if args.seed not in protocol["training_seeds"]:
        raise SystemExit("seed is not registered by the hybrid pilot protocol")
    if not args.execution_id.strip():
        raise SystemExit("execution ID must be nonempty")
    try:
        output_dir = require_path_outside_repository_v1(
            repository=REPOSITORY,
            path=args.output_dir,
            label="hybrid pilot result directory",
        )
        source_commit = bound_clean_source_commit_v1(REPOSITORY)
    except ScienceExecutionIOV1Error as error:
        raise SystemExit(str(error)) from error

    output_dir.mkdir(parents=True, exist_ok=True)
    stem = f"{args.arm.lower()}-seed-{args.seed}"
    result_path = output_dir / f"{stem}.json"
    model_path = output_dir / f"{stem}.pt"
    if result_path.exists() or model_path.exists():
        raise SystemExit("hybrid pilot output already exists; use a fresh identity")

    result, model = run_hybrid_pilot_seed_arm_v1(
        arm=args.arm,
        seed=args.seed,
        device_name=args.device,
    )
    if result.get("schema") != HYBRID_PILOT_RESULT_SCHEMA_V1:
        raise RuntimeError("hybrid pilot runtime returned a foreign result schema")

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
        "cuda_device_name": (
            torch.cuda.get_device_name(torch.device(args.device))
            if args.device.startswith("cuda")
            else None
        ),
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
                "pilot_scientific_gate": "NOT_RUN",
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
