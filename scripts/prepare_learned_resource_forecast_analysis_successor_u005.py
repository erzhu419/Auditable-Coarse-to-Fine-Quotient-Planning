#!/usr/bin/env python3
"""Ratify the one-shot U005 analysis-only successor and its fixed paths."""

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
from acfqp.science.learned_resource_forecast_analysis_successor_protocol_v1 import (
    ANALYSIS_OUTPUT_FILENAMES_V1,
    LearnedResourceForecastAnalysisSuccessorProtocolV1Error,
    build_ratified_analysis_successor_protocol_v1,
    validate_ratified_analysis_successor_protocol_v1,
)


REPOSITORY = Path(__file__).resolve().parents[1]
FIXED_SOURCE_CHECKOUT = Path(
    "/home/erzhu419/mine_code/"
    "acfqp-learned-resource-forecast-2048-pilot-u005-source"
)
FIXED_LAUNCH_ROOT = Path(
    "/home/erzhu419/mine_code/"
    "acfqp-learned-resource-forecast-2048-pilot-u005-launch"
)
FIXED_ANALYSIS_ROOT = Path(
    "/home/erzhu419/mine_code/"
    "acfqp-learned-resource-forecast-2048-pilot-u005-analysis"
)
FIXED_STATUS_ROOT = Path(
    "/home/erzhu419/mine_code/"
    "acfqp-learned-resource-forecast-2048-pilot-u005-status"
)
FIXED_RETAINED_ROOT = Path(
    "/home/erzhu419/mine_code/"
    "acfqp-learned-resource-forecast-2048-pilot-u005-retained"
)
FIXED_PROTOCOL_PATH = FIXED_LAUNCH_ROOT / "protocol.json"
FIXED_MANIFEST_PATH = FIXED_LAUNCH_ROOT / "launch-manifest.json"
FIXED_AUTHORITY_RECEIPT_PATH = FIXED_LAUNCH_ROOT / "authority-scan-receipt.json"
FIXED_STATUS_PATH = FIXED_STATUS_ROOT / "analysis-postprocess.jsonl"
COMMON_PYTHON = "/home/erzhu419/.venvs/scheduleurm-torch-bench/bin/python"
MANIFEST_SCHEMA_V1 = (
    "acfqp.science.learned_resource_forecast_2048_analysis_successor_u005_manifest.v1"
)


class LearnedResourceForecastAnalysisSuccessorPreparationV1Error(RuntimeError):
    """The U005 deployment, output roots, or analysis roster changed."""


def build_launch_manifest_v1(protocol: dict[str, Any]) -> dict[str, Any]:
    frozen = validate_ratified_analysis_successor_protocol_v1(protocol)
    training = frozen["predecessor_training_authority"]
    evidence = frozen["predecessor_evidence_authority"]
    fixed_paths = {
        "source_checkout": str(FIXED_SOURCE_CHECKOUT),
        "source_pythonpath": str(FIXED_SOURCE_CHECKOUT / "src"),
        "launch_root": str(FIXED_LAUNCH_ROOT),
        "protocol": str(FIXED_PROTOCOL_PATH),
        "manifest": str(FIXED_MANIFEST_PATH),
        "authority_scan_receipt": str(FIXED_AUTHORITY_RECEIPT_PATH),
        "analysis_root": str(FIXED_ANALYSIS_ROOT),
        "status_root": str(FIXED_STATUS_ROOT),
        "analysis_status": str(FIXED_STATUS_PATH),
        "retained_root": str(FIXED_RETAINED_ROOT),
        "u002_protocol": training["protocol_path"],
        "u002_manifest": training["manifest_path"],
        "u002_results_root": training["results_root"],
        "u002_status_root": training["status_root"],
        "u004_protocol": evidence["protocol_path"],
        "u004_manifest": evidence["manifest_path"],
        "u004_history_scan_receipt": evidence["history_scan_receipt_path"],
        "u004_gather_transport_marker": evidence["gather_transport_marker_path"],
        "u004_gather_receipt": evidence["gather_receipt_path"],
        "u004_failed_postprocess_status": evidence[
            "failed_postprocess_status_path"
        ],
        "u004_results_root": evidence["results_root"],
        "u004_status_root": evidence["status_root"],
        "u004_log_root": evidence["log_root"],
        "u004_failed_analysis_root": evidence["failed_analysis_root"],
        "u004_uncreated_retained_root": evidence["uncreated_retained_root"],
    }
    return {
        "schema": MANIFEST_SCHEMA_V1,
        "protocol_id": frozen["protocol_id"],
        "source_commit": frozen["source_commit"],
        "pilot_execution_identity": frozen["pilot_execution_identity"],
        "analysis_execution_id": frozen["analysis_execution_id"],
        "source_checkout": str(FIXED_SOURCE_CHECKOUT),
        "source_pythonpath": str(FIXED_SOURCE_CHECKOUT / "src"),
        "fixed_paths": fixed_paths,
        "predecessor_training_authority": dict(training),
        "predecessor_evidence_authority": dict(evidence),
        "frozen_analysis_contract": frozen["frozen_analysis_contract"],
        "phase_roster": ["analysis", "independent_verification", "retention"],
        "analysis_jobs": [
            {
                "execution_id": frozen["analysis_execution_id"],
                "host_alias": "jtl110gpu2",
                "expected_hostname": "erzhu419-Super-Server",
                "analysis_device": "cuda:0",
                "verifier_device": "cuda:0",
                "status_path": str(FIXED_STATUS_PATH),
                "output_root": str(FIXED_ANALYSIS_ROOT),
            }
        ],
        "new_training_execution_ids": [],
        "new_evidence_execution_ids": [],
        "new_tape_roots": [],
        "required_runtime": {
            "python_path": COMMON_PYTHON,
            "source_pythonpath": str(FIXED_SOURCE_CHECKOUT / "src"),
            "pythonpath_environment_must_equal_source_pythonpath": True,
            "analysis_device": "cuda:0",
            "verifier_device": "cuda:0",
        },
        "expected_counts": {
            "read_only_u002_training_jobs": 144,
            "read_only_u002_model_snapshots": 432,
            "read_only_u004_evidence_jobs": 432,
            "new_training_jobs": 0,
            "new_evidence_jobs": 0,
            "new_tape_roots": 0,
            "analysis_jobs": 1,
            "analysis_output_files": len(ANALYSIS_OUTPUT_FILENAMES_V1),
        },
    }


def _prepare(output_root: Path) -> dict[str, Any]:
    root = require_path_outside_repository_v1(
        repository=REPOSITORY,
        path=output_root,
        label="U005 analysis-successor launch root",
    )
    if root != FIXED_LAUNCH_ROOT.resolve():
        raise LearnedResourceForecastAnalysisSuccessorPreparationV1Error(
            "U005 launch root differs from its fixed identity path"
        )
    if REPOSITORY.resolve() != FIXED_SOURCE_CHECKOUT.resolve():
        raise LearnedResourceForecastAnalysisSuccessorPreparationV1Error(
            "U005 checkout differs from its fixed deployment path"
        )
    source_commit = bound_clean_source_commit_v1(REPOSITORY)
    protocol = build_ratified_analysis_successor_protocol_v1(source_commit)
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
        "analysis_execution_id": protocol["analysis_execution_id"],
        "output_root": str(root),
        "formal_analysis_identity_consumed": False,
        **manifest["expected_counts"],
    }


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, default=FIXED_LAUNCH_ROOT)
    return parser.parse_args()


def main() -> int:
    try:
        summary = _prepare(_arguments().output_root)
    except (
        ScienceExecutionIOV1Error,
        LearnedResourceForecastAnalysisSuccessorProtocolV1Error,
        LearnedResourceForecastAnalysisSuccessorPreparationV1Error,
    ) as error:
        raise SystemExit(str(error)) from error
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
