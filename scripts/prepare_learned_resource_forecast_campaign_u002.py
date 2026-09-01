#!/usr/bin/env python3
"""Ratify U002 and write its fixed six-GPU launch manifest once."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
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
    expected_player_evidence_execution_id_v1,
)
from acfqp.science.learned_resource_forecast_protocol_v1 import (
    EXPECTED_MODEL_SNAPSHOT_COUNT_V1,
    EXPECTED_PLAYER_COUNT_V1,
    EXPECTED_TRAINING_JOB_COUNT_V1,
    LEARNED_RESOURCE_FORECAST_CHECKPOINTS_V1,
    LEARNED_RESOURCE_FORECAST_TEST_SEEDS_V1,
    LEARNED_RESOURCE_FORECAST_TRAINING_SEEDS_V1,
    LEARNED_RESOURCE_FORECAST_TRAIN_SEEDS_V1,
    build_ratified_learned_resource_forecast_protocol_v1,
    player_key_v1,
    validate_ratified_learned_resource_forecast_protocol_v1,
)
from acfqp.science.matched_double_dqn_2048_learned_resource_pilot_v1 import (
    expected_policy_training_execution_id_v1,
    policy_checkpoint_filename_v1,
)


REPOSITORY = Path(__file__).resolve().parents[1]
FIXED_SOURCE_CHECKOUT = Path(
    "/home/erzhu419/mine_code/"
    "acfqp-learned-resource-forecast-2048-pilot-u002-source"
)
FIXED_SOURCE_PYTHONPATH = FIXED_SOURCE_CHECKOUT / "src"
FIXED_LAUNCH_ROOT = Path(
    "/home/erzhu419/mine_code/"
    "acfqp-learned-resource-forecast-2048-pilot-u002-launch"
)
FIXED_RESULTS_ROOT = Path(
    "/home/erzhu419/mine_code/"
    "acfqp-learned-resource-forecast-2048-pilot-u002-results"
)
FIXED_STATUS_ROOT = Path(
    "/home/erzhu419/mine_code/"
    "acfqp-learned-resource-forecast-2048-pilot-u002-status"
)
FIXED_LOG_ROOT = Path(
    "/home/erzhu419/mine_code/"
    "acfqp-learned-resource-forecast-2048-pilot-u002-logs"
)
FIXED_ANALYSIS_ROOT = Path(
    "/home/erzhu419/mine_code/"
    "acfqp-learned-resource-forecast-2048-pilot-u002-analysis"
)
FIXED_RETAINED_ROOT = Path(
    "/home/erzhu419/mine_code/"
    "acfqp-learned-resource-forecast-2048-pilot-u002-retained"
)
FIXED_PROTOCOL_PATH = FIXED_LAUNCH_ROOT / "protocol.json"
FIXED_MANIFEST_PATH = FIXED_LAUNCH_ROOT / "launch-manifest.json"
FIXED_HISTORY_SCAN_RECEIPT_PATH = FIXED_LAUNCH_ROOT / "history-scan-receipt.json"
FIXED_GATHER_TRANSPORT_MARKER_PATH = (
    FIXED_LAUNCH_ROOT / "gather-transport-marker.json"
)
FIXED_GATHER_RECEIPT_PATH = FIXED_LAUNCH_ROOT / "gather-receipt.json"
FIXED_TRAINING_DISPATCH_STATUS_PATH = (
    FIXED_LAUNCH_ROOT / "training-dispatch.jsonl"
)
FIXED_EVIDENCE_DISPATCH_STATUS_PATH = (
    FIXED_LAUNCH_ROOT / "evidence-dispatch.jsonl"
)
FIXED_POSTPROCESS_STATUS_PATH = FIXED_LAUNCH_ROOT / "postprocess-status.jsonl"
LAUNCH_MANIFEST_SCHEMA_V1 = (
    "acfqp.science.learned_resource_forecast_2048_launch_manifest.v1"
)
COMMON_PYTHON = "/home/erzhu419/.venvs/scheduleurm-torch-bench/bin/python"
WORKER_BINDINGS_V1 = (
    ("jtl110gpu2", "erzhu419-Super-Server", "cuda:0"),
    ("jtl110gpu2", "erzhu419-Super-Server", "cuda:1"),
    ("jtl110gpu", "huiwei-Super-Server", "cuda:0"),
    ("jtl110gpu", "huiwei-Super-Server", "cuda:1"),
    ("jtl311linux", "zhengliang-C246-WU4", "cuda:0"),
    ("jtl311linux", "zhengliang-C246-WU4", "cuda:1"),
)


class LearnedResourceForecastPreparationV1Error(RuntimeError):
    """The clean commit or fixed six-worker roster is not exact."""


def _worker_for_seed(seed: int) -> int:
    if seed not in LEARNED_RESOURCE_FORECAST_TRAINING_SEEDS_V1:
        raise LearnedResourceForecastPreparationV1Error(
            "launch seed is outside the frozen U002 roster"
        )
    return (seed - LEARNED_RESOURCE_FORECAST_TRAINING_SEEDS_V1[0]) % len(
        WORKER_BINDINGS_V1
    )


def build_launch_manifest_v1(protocol: dict[str, Any]) -> dict[str, Any]:
    """Build the interleaved host/GPU roster without consuming an identity."""

    frozen = validate_ratified_learned_resource_forecast_protocol_v1(protocol)
    workers: list[dict[str, Any]] = []
    all_training_jobs: list[dict[str, Any]] = []
    all_evidence_jobs: list[dict[str, Any]] = []
    for worker_index, (host_alias, hostname, device) in enumerate(
        WORKER_BINDINGS_V1
    ):
        seeds = [
            seed
            for seed in frozen["training_seeds"]
            if _worker_for_seed(seed) == worker_index
        ]
        training_jobs: list[dict[str, Any]] = []
        evidence_jobs: list[dict[str, Any]] = []
        for seed in seeds:
            for arm in frozen["arms"]:
                checkpoint_files = [
                    policy_checkpoint_filename_v1(
                        arm=arm, seed=seed, checkpoint=checkpoint
                    )
                    for checkpoint in LEARNED_RESOURCE_FORECAST_CHECKPOINTS_V1
                ]
                training_jobs.append(
                    {
                        "seed": seed,
                        "arm": arm,
                        "execution_id": expected_policy_training_execution_id_v1(
                            frozen, arm=arm, seed=seed
                        ),
                        "result_filename": f"{arm.lower()}-seed-{seed}.json",
                        "checkpoint_filenames": checkpoint_files,
                    }
                )
                for checkpoint, model_filename in zip(
                    LEARNED_RESOURCE_FORECAST_CHECKPOINTS_V1,
                    checkpoint_files,
                    strict=True,
                ):
                    stem = f"{arm.lower()}-seed-{seed}-checkpoint-{checkpoint}"
                    train_split = seed in LEARNED_RESOURCE_FORECAST_TRAIN_SEEDS_V1
                    evidence_jobs.append(
                        {
                            "player_key": player_key_v1(seed, arm, checkpoint),
                            "seed": seed,
                            "arm": arm,
                            "checkpoint": checkpoint,
                            "split": "TRAIN" if train_split else "TEST",
                            "execution_id": expected_player_evidence_execution_id_v1(
                                frozen,
                                generator_arm=arm,
                                base_seed=seed,
                                checkpoint=checkpoint,
                            ),
                            "model_filename": model_filename,
                            "label_filename": f"{stem}.label.json",
                            "probe_filename": f"{stem}.probe.json",
                            "trajectory_metadata_filename": (
                                f"{stem}.trajectory.json" if train_split else None
                            ),
                            "trajectory_array_filename": (
                                f"{stem}.trajectory.npz" if train_split else None
                            ),
                        }
                    )
        worker = {
            "worker": worker_index,
            "host_alias": host_alias,
            "expected_hostname": hostname,
            "device": device,
            "python": COMMON_PYTHON,
            "seeds": seeds,
            "train_seed_count": sum(
                seed in LEARNED_RESOURCE_FORECAST_TRAIN_SEEDS_V1 for seed in seeds
            ),
            "test_seed_count": sum(
                seed in LEARNED_RESOURCE_FORECAST_TEST_SEEDS_V1 for seed in seeds
            ),
            "policy_training_status_stream": f"worker-{worker_index}-training.jsonl",
            "player_evidence_status_stream": f"worker-{worker_index}-evidence.jsonl",
            "policy_training_jobs": training_jobs,
            "player_evidence_jobs": evidence_jobs,
        }
        workers.append(worker)
        all_training_jobs.extend(training_jobs)
        all_evidence_jobs.extend(evidence_jobs)
    if (
        [len(worker["seeds"]) for worker in workers] != [8] * 6
        or len(all_training_jobs) != EXPECTED_TRAINING_JOB_COUNT_V1
        or len(all_evidence_jobs) != EXPECTED_PLAYER_COUNT_V1
        or sum(
            len(job["checkpoint_filenames"]) for job in all_training_jobs
        )
        != EXPECTED_MODEL_SNAPSHOT_COUNT_V1
        or len({job["execution_id"] for job in all_training_jobs})
        != EXPECTED_TRAINING_JOB_COUNT_V1
        or len({job["execution_id"] for job in all_evidence_jobs})
        != EXPECTED_PLAYER_COUNT_V1
        or len({job["player_key"] for job in all_evidence_jobs})
        != EXPECTED_PLAYER_COUNT_V1
    ):
        raise LearnedResourceForecastPreparationV1Error(
            "six-worker launch roster does not close the frozen matrices"
        )
    return {
        "schema": LAUNCH_MANIFEST_SCHEMA_V1,
        "protocol_id": frozen["protocol_id"],
        "source_commit": frozen["source_commit"],
        "source_checkout": str(FIXED_SOURCE_CHECKOUT),
        "source_pythonpath": str(FIXED_SOURCE_PYTHONPATH),
        "fixed_paths": {
            "source_checkout": str(FIXED_SOURCE_CHECKOUT),
            "source_pythonpath": str(FIXED_SOURCE_PYTHONPATH),
            "launch_root": str(FIXED_LAUNCH_ROOT),
            "protocol": str(FIXED_PROTOCOL_PATH),
            "manifest": str(FIXED_MANIFEST_PATH),
            "history_scan_receipt": str(FIXED_HISTORY_SCAN_RECEIPT_PATH),
            "gather_transport_marker": str(FIXED_GATHER_TRANSPORT_MARKER_PATH),
            "gather_receipt": str(FIXED_GATHER_RECEIPT_PATH),
            "results_root": str(FIXED_RESULTS_ROOT),
            "status_root": str(FIXED_STATUS_ROOT),
            "log_root": str(FIXED_LOG_ROOT),
            "analysis_root": str(FIXED_ANALYSIS_ROOT),
            "retained_root": str(FIXED_RETAINED_ROOT),
            "training_dispatch_status": str(
                FIXED_TRAINING_DISPATCH_STATUS_PATH
            ),
            "evidence_dispatch_status": str(
                FIXED_EVIDENCE_DISPATCH_STATUS_PATH
            ),
            "postprocess_status": str(FIXED_POSTPROCESS_STATUS_PATH),
        },
        "history_scan_contract": {
            "scan_root": "/home/erzhu419/mine_code",
            "excluded_current_roots": [
                str(FIXED_SOURCE_CHECKOUT),
                str(FIXED_LAUNCH_ROOT),
            ],
            "blocking_token_kinds": [
                "pilot_execution_identity",
                "execution_id",
                "frozen_tape_root",
                "fixed_campaign_artifact_path",
            ],
            "frozen_tape_roots": [
                frozen["training_tape_prefix"],
                frozen["evaluation_tape_prefix"],
                frozen["trajectory_tape_root"],
                frozen["label_tape_root"],
                frozen["probe_tape_root"],
            ],
            "fixed_campaign_artifact_paths": [
                str(FIXED_RESULTS_ROOT),
                str(FIXED_STATUS_ROOT),
                str(FIXED_LOG_ROOT),
                str(FIXED_ANALYSIS_ROOT),
                str(FIXED_RETAINED_ROOT),
            ],
            "registered_seed_roster_retained": True,
            "bare_seed_global_match_is_execution_identity": False,
            "reason": (
                "AN_INTEGER_SEED_IN_AN_UNRELATED_PROJECT_DOES_NOT_SHARE_THIS_"
                "PILOT_EXECUTION_ID_TAPES_OR_INITIALIZATION_CONTEXT"
            ),
        },
        "pilot_execution_identity": frozen["pilot_execution_identity"],
        "worker_count": len(workers),
        "assignment": (
            "ROUND_ROBIN_BASE_SEED_ACROSS_SIX_GPUS;_ALL_ARMS_AND_CHECKPOINTS_"
            "FOR_ONE_BASE_SEED_SHARE_ONE_HOST_AND_GPU"
        ),
        "train_and_test_seeds_interleaved_across_hosts": True,
        "required_runtime": {
            "python_implementation": "CPython",
            "python_version": "3.11.15",
            "torch_version": "2.5.1+cu121",
            "torch_cuda_runtime_version": "12.1",
            "numpy_version": "2.4.4",
            "scipy_version": "1.17.1",
            "python_path": COMMON_PYTHON,
            "source_pythonpath": str(FIXED_SOURCE_PYTHONPATH),
            "acfqp_import_must_resolve_inside_source_pythonpath": True,
            "pythonpath_environment_must_equal_source_pythonpath": True,
            "global_preflight_optimizer_smoke_required": True,
            "optimizer_smoke_device": "cpu",
            "optimizer_smoke_linear_layer_count": 1,
            "optimizer_smoke_module": "torch.nn.Linear",
            "optimizer_smoke_optimizer": "torch.optim.Adam",
        },
        "workers": workers,
        "expected_counts": {
            "policy_training_jobs": EXPECTED_TRAINING_JOB_COUNT_V1,
            "model_snapshots": EXPECTED_MODEL_SNAPSHOT_COUNT_V1,
            "player_evidence_jobs": EXPECTED_PLAYER_COUNT_V1,
            "trajectory_player_artifacts": 288,
            "complete_trajectory_episodes": 4_608,
            "label_aggregates": EXPECTED_PLAYER_COUNT_V1,
            "exact_eight_action_probe_records": 6_912,
        },
        "central_analysis": {
            "host_alias": "jtl110gpu2",
            "expected_hostname": "erzhu419-Super-Server",
            "device": "cuda:0",
            "fit_encoders_before_opening_probe_files": True,
            "encode_probes_before_opening_label_files": True,
            "label_join_is_final_analysis_stage": True,
        },
    }


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output-root", type=Path, default=FIXED_LAUNCH_ROOT
    )
    return parser.parse_args()


def _prepare(output_root: Path) -> dict[str, Any]:
    root = require_path_outside_repository_v1(
        repository=REPOSITORY,
        path=output_root,
        label="U002 launch preparation root",
    )
    if root != FIXED_LAUNCH_ROOT.resolve():
        raise LearnedResourceForecastPreparationV1Error(
            "U002 launch preparation root differs from its fixed identity path"
        )
    source_commit = bound_clean_source_commit_v1(REPOSITORY)
    if REPOSITORY.resolve() != FIXED_SOURCE_CHECKOUT.resolve():
        raise LearnedResourceForecastPreparationV1Error(
            "U002 preparation checkout differs from the fixed deployment path"
        )
    protocol = build_ratified_learned_resource_forecast_protocol_v1(source_commit)
    manifest = build_launch_manifest_v1(protocol)
    write_exclusive_bytes_v1(root / "protocol.json", canonical_json_bytes(protocol))
    write_exclusive_bytes_v1(
        root / "launch-manifest.json", canonical_json_bytes(manifest)
    )
    return {
        "success": True,
        "source_commit": source_commit,
        "protocol_id": protocol["protocol_id"],
        "pilot_execution_identity": protocol["pilot_execution_identity"],
        "worker_count": manifest["worker_count"],
        **manifest["expected_counts"],
        "output_root": str(root),
    }


def main() -> int:
    try:
        summary = _prepare(_arguments().output_root)
    except (
        ScienceExecutionIOV1Error,
        LearnedResourceForecastPreparationV1Error,
    ) as error:
        raise SystemExit(str(error)) from error
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
