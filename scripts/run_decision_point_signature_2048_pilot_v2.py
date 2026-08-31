#!/usr/bin/env python3
"""Prepare, collect, and evaluate the decision-point signature V2 pilot."""

from __future__ import annotations

import argparse
import gc
import json
from pathlib import Path
import platform
import socket
import sys
from typing import Any

from acfqp.phase3e_ids import canonical_json_bytes
from acfqp.science.decision_point_signature_2048_pilot_v2 import (
    FrozenDecisionStateV2,
    collect_policy_decision_evidence_v2,
    load_candidate_policy_v2,
)
from acfqp.science.decision_point_signature_evaluator_v2 import (
    DecisionPointSignatureEvaluatorV2Error,
    WORKER_EVIDENCE_SCHEMA_V2,
    evaluate_decision_point_pilot_v2,
)
from acfqp.science.decision_point_signature_protocol_v2 import (
    DecisionPointSignatureProtocolV2Error,
    build_decision_point_protocol_v2,
    validate_decision_point_protocol_v2,
)
from acfqp.science.execution_io_v1 import (
    ScienceExecutionIOV1Error,
    bound_clean_source_commit_v1,
    require_path_outside_repository_v1,
    write_exclusive_bytes_v1,
)
from acfqp.science.hybrid_confirmatory_evaluator_v2 import (
    load_evidence_bound_hybrid_confirmatory_matrix_v2,
)


REPOSITORY = Path(__file__).resolve().parents[1]
WORKER_COUNT = 2
LAUNCH_MANIFEST_SCHEMA = (
    "acfqp.science.decision_point_signature_2048_launch_manifest.v2"
)


class DecisionPointSignaturePilotCLIError(RuntimeError):
    """One V2 execution request or retained document is invalid."""


def _read_object(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise DecisionPointSignaturePilotCLIError(
            f"cannot read {label} as one JSON object: {path}"
        ) from error
    if type(value) is not dict:
        raise DecisionPointSignaturePilotCLIError(
            f"{label} must contain one JSON object"
        )
    return value


def _outside(path: Path, label: str) -> Path:
    return require_path_outside_repository_v1(
        repository=REPOSITORY,
        path=path,
        label=label,
    )


def _runtime_context(device_name: str) -> dict[str, Any]:
    """Return the exact typed runtime record expected by the evaluator."""

    import numpy as np
    import scipy
    import torch

    device = torch.device(device_name)
    if device.type == "cuda":
        if not torch.cuda.is_available():
            raise DecisionPointSignaturePilotCLIError(
                "requested CUDA worker device is unavailable"
            )
        device_description = str(torch.cuda.get_device_name(device))
    else:
        device_description = None
    cuda_runtime = (
        None if torch.version.cuda is None else str(torch.version.cuda)
    )
    raw_cudnn_version = torch.backends.cudnn.version()
    cudnn_version = (
        None if raw_cudnn_version is None else int(raw_cudnn_version)
    )
    context = {
        "hostname": str(socket.gethostname()),
        "python_version": str(platform.python_version()),
        "numpy_version": str(np.__version__),
        "scipy_version": str(scipy.__version__),
        "torch_version": str(torch.__version__),
        "torch_cuda_runtime_version": cuda_runtime,
        "torch_cudnn_version": cudnn_version,
        "device": str(device),
        "cuda_device_name": device_description,
    }
    if any(
        type(context[field]) is not str or not context[field]
        for field in (
            "hostname",
            "python_version",
            "numpy_version",
            "scipy_version",
            "torch_version",
            "device",
        )
    ):
        raise DecisionPointSignaturePilotCLIError(
            "runtime context identity fields must be exact builtin strings"
        )
    return context


def _launch_manifest(protocol: dict[str, Any]) -> dict[str, Any]:
    workers = []
    for worker_index in range(WORKER_COUNT):
        roster = [
            row
            for row in protocol["candidate_models"]
            if row["worker"] == worker_index
        ]
        workers.append(
            {
                "worker": worker_index,
                "device": f"cuda:{worker_index}",
                "execution_id": (
                    f"{protocol['pilot_execution_identity']}:worker:{worker_index}"
                ),
                "worker_document": f"worker-{worker_index}.json",
                "policy_count": len(roster),
                "policy_seeds": [row["seed"] for row in roster],
                "model_filenames": [row["model_filename"] for row in roster],
            }
        )
    if [row["policy_count"] for row in workers] != [12, 12]:
        raise DecisionPointSignaturePilotCLIError(
            "the launch manifest no longer has two fixed 12-policy workers"
        )
    return {
        "schema": LAUNCH_MANIFEST_SCHEMA,
        "protocol_id": protocol["protocol_id"],
        "source_commit": protocol["source_commit"],
        "pilot_execution_identity": protocol["pilot_execution_identity"],
        "worker_count": WORKER_COUNT,
        "workers": workers,
        "evaluation_output": "pilot-result.json",
    }


def _prepare(args: argparse.Namespace) -> dict[str, Any]:
    output_root = _outside(args.output_root, "pilot preparation output root")
    parent_protocol_path = _outside(
        args.parent_protocol, "retained u005 protocol input"
    )
    parent_manifest_path = _outside(
        args.parent_manifest, "retained u005 launch manifest input"
    )
    prior_result_path = _outside(
        args.prior_result, "retained V1 pilot-result input"
    )
    source_commit = bound_clean_source_commit_v1(REPOSITORY)
    protocol = build_decision_point_protocol_v2(
        _read_object(parent_protocol_path, "retained u005 protocol"),
        _read_object(parent_manifest_path, "retained u005 manifest"),
        _read_object(prior_result_path, "retained V1 pilot result"),
        source_commit,
    )
    protocol = validate_decision_point_protocol_v2(protocol)
    manifest = _launch_manifest(protocol)
    write_exclusive_bytes_v1(
        output_root / "protocol.json", canonical_json_bytes(protocol)
    )
    write_exclusive_bytes_v1(
        output_root / "launch-manifest.json", canonical_json_bytes(manifest)
    )
    return {
        "success": True,
        "operation": "prepare",
        "protocol_id": protocol["protocol_id"],
        "source_commit": source_commit,
        "pilot_execution_identity": protocol["pilot_execution_identity"],
        "candidate_policy_count": len(protocol["candidate_models"]),
        "decision_state_count": len(protocol["decision_states"]),
        "output_root": str(output_root),
    }


def _validate_parent_binding(
    *,
    protocol: dict[str, Any],
    parent_root: Path,
    prior_result_path: Path,
    source_commit: str,
) -> None:
    parent_protocol = _read_object(parent_root / "protocol.json", "parent protocol")
    parent_manifest = _read_object(parent_root / "manifest.json", "parent manifest")
    prior_result = _read_object(prior_result_path, "retained V1 pilot result")
    rebuilt = build_decision_point_protocol_v2(
        parent_protocol, parent_manifest, prior_result, source_commit
    )
    if canonical_json_bytes(rebuilt) != canonical_json_bytes(protocol):
        raise DecisionPointSignaturePilotCLIError(
            "runtime parent/prior evidence does not rebuild the ratified V2 protocol"
        )
    parent_matrix = load_evidence_bound_hybrid_confirmatory_matrix_v2(
        protocol=parent_protocol,
        manifest=parent_manifest,
        results_root=parent_root,
    )
    if len(parent_matrix) != 72:
        raise DecisionPointSignaturePilotCLIError(
            "retained u005 evidence does not close the exact 72-job parent matrix"
        )


def _worker(args: argparse.Namespace) -> dict[str, Any]:
    protocol_path = _outside(args.protocol, "pilot protocol input")
    parent_root = _outside(args.parent_root, "retained u005 evidence root")
    prior_result_path = _outside(args.prior_result, "retained V1 pilot-result input")
    output = _outside(args.output, "pilot worker output")
    protocol = validate_decision_point_protocol_v2(
        _read_object(protocol_path, "pilot protocol")
    )
    source_commit = bound_clean_source_commit_v1(REPOSITORY)
    if protocol["source_commit"] != source_commit:
        raise DecisionPointSignaturePilotCLIError(
            "pilot protocol source commit differs from the runtime checkout"
        )
    if args.worker not in range(WORKER_COUNT):
        raise DecisionPointSignaturePilotCLIError("worker must be 0 or 1")
    expected_device = f"cuda:{args.worker}"
    if args.device != expected_device:
        raise DecisionPointSignaturePilotCLIError(
            "pilot worker device differs from its fixed worker binding"
        )
    _validate_parent_binding(
        protocol=protocol,
        parent_root=parent_root,
        prior_result_path=prior_result_path,
        source_commit=source_commit,
    )
    roster = [
        row for row in protocol["candidate_models"] if row["worker"] == args.worker
    ]
    if len(roster) != 12:
        raise DecisionPointSignaturePilotCLIError(
            "pilot worker does not own exactly twelve fixed policies"
        )
    state_library = tuple(
        FrozenDecisionStateV2.from_document(row)
        for row in protocol["decision_states"]
    )
    if len(state_library) != 64:
        raise DecisionPointSignaturePilotCLIError(
            "pilot protocol no longer contains exactly 64 decision states"
        )

    import torch

    policy_evidence: list[dict[str, Any]] = []
    print(
        json.dumps(
            {
                "event": "WORKER_STARTED",
                "protocol_id": protocol["protocol_id"],
                "worker": args.worker,
                "device": args.device,
                "policy_count": len(roster),
                "decision_state_count": len(state_library),
            },
            sort_keys=True,
        ),
        flush=True,
    )
    for row in roster:
        model_path = parent_root / "artifacts" / row["model_filename"]
        if not model_path.is_file():
            raise DecisionPointSignaturePilotCLIError(
                f"registered parent candidate model is absent: {model_path}"
            )
        model = load_candidate_policy_v2(model_path, args.device)
        evidence = collect_policy_decision_evidence_v2(
            model,
            state_library=state_library,
            prefix_tape_root=protocol["prefix_tape_root"],
        )
        policy_evidence.append(
            {
                "seed": row["seed"],
                "model_filename": row["model_filename"],
                "parent_execution_id": row["parent_execution_id"],
                "collector": evidence,
            }
        )
        del model
        gc.collect()
        torch.cuda.empty_cache()
        print(
            json.dumps(
                {
                    "event": "POLICY_EVIDENCE_COMPLETED",
                    "worker": args.worker,
                    "seed": row["seed"],
                    "completed_policy_count": len(policy_evidence),
                    "policy_count": len(roster),
                },
                sort_keys=True,
            ),
            flush=True,
        )
    document = {
        "schema": WORKER_EVIDENCE_SCHEMA_V2,
        "protocol_id": protocol["protocol_id"],
        "source_commit": source_commit,
        "pilot_execution_identity": protocol["pilot_execution_identity"],
        "worker": args.worker,
        "device": args.device,
        "execution_id": f"{protocol['pilot_execution_identity']}:worker:{args.worker}",
        "runtime_context": _runtime_context(args.device),
        "policy_count": len(policy_evidence),
        "policy_evidence": policy_evidence,
        "scientific_success_claimed": False,
    }
    write_exclusive_bytes_v1(output, canonical_json_bytes(document))
    return {
        "success": True,
        "operation": "worker",
        "protocol_id": protocol["protocol_id"],
        "worker": args.worker,
        "device": args.device,
        "policy_count": len(policy_evidence),
        "output": str(output),
    }


def _evaluate(args: argparse.Namespace) -> dict[str, Any]:
    protocol_path = _outside(args.protocol, "pilot protocol input")
    output = _outside(args.output, "pilot evaluation output")
    protocol = validate_decision_point_protocol_v2(
        _read_object(protocol_path, "pilot protocol")
    )
    source_commit = bound_clean_source_commit_v1(REPOSITORY)
    if protocol["source_commit"] != source_commit:
        raise DecisionPointSignaturePilotCLIError(
            "pilot protocol source commit differs from evaluator checkout"
        )
    if len(args.worker_document) != WORKER_COUNT:
        raise DecisionPointSignaturePilotCLIError(
            "evaluation requires exactly two worker documents"
        )
    worker_documents = [
        _read_object(_outside(path, "pilot worker document"), "worker document")
        for path in args.worker_document
    ]
    result = evaluate_decision_point_pilot_v2(protocol, worker_documents)
    if type(result) is not dict:
        raise DecisionPointSignaturePilotCLIError(
            "pilot evaluator did not return one JSON object"
        )
    result["evaluation_runtime_context"] = _runtime_context("cpu")
    result["scientific_success_claimed"] = False
    write_exclusive_bytes_v1(output, canonical_json_bytes(result))
    return {
        "success": True,
        "operation": "evaluate",
        "protocol_id": protocol["protocol_id"],
        "output": str(output),
        "provisional_design_signal": result.get(
            "PROVISIONAL_DESIGN_SIGNAL_GATE"
        ),
        "scientific_success_claimed": False,
    }


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="operation", required=True)

    prepare = subparsers.add_parser("prepare")
    prepare.add_argument("--parent-protocol", type=Path, required=True)
    prepare.add_argument("--parent-manifest", type=Path, required=True)
    prepare.add_argument("--prior-result", type=Path, required=True)
    prepare.add_argument("--output-root", type=Path, required=True)

    worker = subparsers.add_parser("worker")
    worker.add_argument("--protocol", type=Path, required=True)
    worker.add_argument("--parent-root", type=Path, required=True)
    worker.add_argument("--prior-result", type=Path, required=True)
    worker.add_argument("--worker", type=int, required=True)
    worker.add_argument("--device", required=True)
    worker.add_argument("--output", type=Path, required=True)

    evaluate = subparsers.add_parser("evaluate")
    evaluate.add_argument("--protocol", type=Path, required=True)
    evaluate.add_argument(
        "--worker-document", type=Path, action="append", required=True
    )
    evaluate.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = _arguments()
    try:
        if args.operation == "prepare":
            summary = _prepare(args)
        elif args.operation == "worker":
            summary = _worker(args)
        else:
            summary = _evaluate(args)
    except (
        DecisionPointSignatureEvaluatorV2Error,
        DecisionPointSignaturePilotCLIError,
        DecisionPointSignatureProtocolV2Error,
        ScienceExecutionIOV1Error,
    ) as error:
        raise SystemExit(str(error)) from error
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
