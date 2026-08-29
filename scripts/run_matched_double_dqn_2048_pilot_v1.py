#!/usr/bin/env python3
"""Run one registered matched Double-DQN pilot seed-arm."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import platform
import socket
import subprocess
import sys

from acfqp.science.matched_double_dqn_2048_v1 import (
    PILOT_ARMS,
    run_pilot_seed_arm_v1,
)
from acfqp.science.latent_resource_protocol_v1 import build_pilot_protocol_v1


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--arm", required=True, choices=PILOT_ARMS)
    parser.add_argument("--seed", required=True, type=int)
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--execution-id", required=True)
    return parser.parse_args()


def _write_exclusive(path: Path, raw: bytes) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC
    fd = os.open(path, flags, 0o600)
    try:
        view = memoryview(raw)
        while view:
            written = os.write(fd, view)
            view = view[written:]
        os.fsync(fd)
    finally:
        os.close(fd)


def _bound_clean_source_commit(output_dir: Path) -> str:
    repository = Path(__file__).resolve().parents[1]
    resolved_output = output_dir.resolve()
    if resolved_output == repository or repository in resolved_output.parents:
        raise SystemExit("pilot output directory must be outside the source checkout")
    head = subprocess.run(
        ["git", "-C", str(repository), "rev-parse", "--verify", "HEAD^{commit}"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    status = subprocess.run(
        ["git", "-C", str(repository), "status", "--porcelain", "--untracked-files=all"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    if len(head) != 40 or any(character not in "0123456789abcdef" for character in head):
        raise SystemExit("current source HEAD is not one full Git object ID")
    if status:
        raise SystemExit("pilot source checkout is not clean")
    return head


def main() -> int:
    args = _arguments()
    protocol = build_pilot_protocol_v1()
    if args.seed not in protocol["training_seeds"]:
        raise SystemExit("seed is not registered by the pilot protocol")
    if not args.execution_id.strip():
        raise SystemExit("execution ID must be nonempty")
    source_commit = _bound_clean_source_commit(args.output_dir)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    stem = f"{args.arm.lower()}-seed-{args.seed}"
    result_path = args.output_dir / f"{stem}.json"
    model_path = args.output_dir / f"{stem}.pt"
    if result_path.exists() or model_path.exists():
        raise SystemExit("pilot output already exists; choose a fresh output directory")
    result, model = run_pilot_seed_arm_v1(
        arm=args.arm,
        seed=args.seed,
        device_name=args.device,
    )
    import torch
    import numpy as np

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

    torch.save(model.state_dict(), model_path)
    _write_exclusive(
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
                "arm": args.arm,
                "seed": args.seed,
                "result": str(result_path),
                "model": str(model_path),
                "execution_id": args.execution_id,
                "source_commit": source_commit,
                "pilot_scientific_gate": "NOT_RUN",
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
