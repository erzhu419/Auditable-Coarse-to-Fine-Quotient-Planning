#!/usr/bin/env python3
"""Write the one-shot three-host zero-hit authority receipt for U005."""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import shlex
import subprocess
import sys
from typing import Any, Callable

from acfqp.phase3e_ids import canonical_json_bytes
from acfqp.science.execution_io_v1 import (
    ScienceExecutionIOV1Error,
    bound_clean_source_commit_v1,
    require_path_outside_repository_v1,
    write_exclusive_bytes_v1,
)
from acfqp.science.learned_resource_forecast_analysis_successor_protocol_v1 import (
    LearnedResourceForecastAnalysisSuccessorProtocolV1Error,
    validate_ratified_analysis_successor_protocol_v1,
)


REPOSITORY = Path(__file__).resolve().parents[1]
SCHEMA_V1 = (
    "acfqp.science.learned_resource_forecast_analysis_successor_history_scan.u005.v1"
)
DEFAULT_SCAN_ROOT = Path("/home/erzhu419/mine_code")
HOSTS_V1 = (
    ("jtl110gpu2", "erzhu419-Super-Server"),
    ("jtl110gpu", "huiwei-Super-Server"),
    ("jtl311linux", "zhengliang-C246-WU4"),
)
SSH_NO_MUX_OPTIONS_V1 = (
    "-o",
    "BatchMode=yes",
    "-o",
    "ControlMaster=no",
    "-o",
    "ControlPath=none",
)
HostScannerV1 = Callable[[str, dict[str, Any]], dict[str, Any]]


class LearnedResourceForecastAnalysisHistoryU005Error(RuntimeError):
    """The U005 global zero-hit scan is incomplete or non-fresh."""


def _load_script(name: str, filename: str):
    path = REPOSITORY / "scripts" / filename
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise LearnedResourceForecastAnalysisHistoryU005Error(
            f"cannot load history dependency: {path}"
        )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _prepare_module():
    return _load_script(
        "acfqp_u005_prepare_for_history",
        "prepare_learned_resource_forecast_analysis_successor_u005.py",
    )


def _base_scan_module():
    return _load_script(
        "acfqp_u002_history_engine_for_u005",
        "scan_learned_resource_forecast_history_u002.py",
    )


def _read_object(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise LearnedResourceForecastAnalysisHistoryU005Error(
            f"cannot read {label}: {path}"
        ) from error
    if type(value) is not dict:
        raise LearnedResourceForecastAnalysisHistoryU005Error(
            f"{label} must contain one JSON object"
        )
    return value


def _expected_request(
    protocol: dict[str, Any], manifest: dict[str, Any], scan_root: Path
) -> dict[str, Any]:
    fixed = manifest["fixed_paths"]
    identity_tokens = [protocol["analysis_execution_id"], protocol["protocol_id"]]
    if (
        manifest["analysis_jobs"][0]["execution_id"]
        != protocol["analysis_execution_id"]
        or manifest["new_training_execution_ids"] != []
        or manifest["new_evidence_execution_ids"] != []
        or manifest["new_tape_roots"] != []
        or len(set(identity_tokens)) != 2
    ):
        raise LearnedResourceForecastAnalysisHistoryU005Error(
            "U005 analysis-only identity roster changed"
        )
    return {
        "protocol": fixed["protocol"],
        "manifest": fixed["manifest"],
        "source_pythonpath": fixed["source_pythonpath"],
        "python": manifest["required_runtime"]["python_path"],
        "scan_root": str(scan_root.resolve()),
        "excluded_roots": [fixed["source_checkout"], fixed["launch_root"]],
        "pilot_execution_identity": protocol["pilot_execution_identity"],
        "execution_ids": identity_tokens,
        "seeds": [],
        "tape_roots": [],
        "campaign_artifact_paths": [
            fixed["analysis_root"],
            fixed["status_root"],
            fixed["retained_root"],
        ],
    }


def _scan_local_host(request: dict[str, Any]) -> dict[str, Any]:
    base = _base_scan_module()
    try:
        return base._scan_local_host(request)  # noqa: SLF001
    except base.LearnedResourceForecastHistoryScanV1Error as error:
        raise LearnedResourceForecastAnalysisHistoryU005Error(str(error)) from error


def _ssh_host_scan(host_alias: str, request: dict[str, Any]) -> dict[str, Any]:
    script = (
        Path(request["source_pythonpath"]).parent
        / "scripts"
        / "scan_learned_resource_forecast_analysis_history_u005.py"
    )
    command = shlex.join(
        [
            "env",
            f"PYTHONPATH={request['source_pythonpath']}",
            request["python"],
            str(script),
            "--host-scan-only",
            "--protocol",
            request["protocol"],
            "--manifest",
            request["manifest"],
            "--scan-root",
            request["scan_root"],
        ]
    )
    completed = subprocess.run(
        ["ssh", *SSH_NO_MUX_OPTIONS_V1, host_alias, command],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise LearnedResourceForecastAnalysisHistoryU005Error(
            f"U005 history scan failed on {host_alias}: {completed.stderr.strip()}"
        )
    try:
        result = json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        raise LearnedResourceForecastAnalysisHistoryU005Error(
            f"U005 history scan on {host_alias} returned no JSON"
        ) from error
    if type(result) is not dict:
        raise LearnedResourceForecastAnalysisHistoryU005Error(
            "U005 host scan returned non-object"
        )
    return result


def validate_authority_scan_receipt_v1(
    receipt: dict[str, Any], protocol: dict[str, Any], manifest: dict[str, Any]
) -> dict[str, Any]:
    request = _expected_request(protocol, manifest, DEFAULT_SCAN_ROOT)
    hosts = receipt.get("hosts")
    if (
        receipt.get("schema") != SCHEMA_V1
        or receipt.get("protocol_id") != protocol["protocol_id"]
        or receipt.get("source_commit") != protocol["source_commit"]
        or receipt.get("pilot_execution_identity")
        != protocol["pilot_execution_identity"]
        or receipt.get("analysis_execution_id") != protocol["analysis_execution_id"]
        or receipt.get("scan_root") != request["scan_root"]
        or receipt.get("excluded_roots") != request["excluded_roots"]
        or receipt.get("scanned_identity_tokens") != request["execution_ids"]
        or receipt.get("new_training_execution_ids") != []
        or receipt.get("new_evidence_execution_ids") != []
        or receipt.get("new_tape_roots") != []
        or receipt.get("campaign_artifact_paths")
        != request["campaign_artifact_paths"]
        or receipt.get("predecessor_authority_tokens_scanned_as_collisions")
        is not False
        or type(hosts) is not list
        or len(hosts) != 3
        or receipt.get("total_match_count") != 0
        or receipt.get("no_prior_identity_hits") is not True
    ):
        raise LearnedResourceForecastAnalysisHistoryU005Error(
            "U005 authority receipt is not the exact three-host zero-hit scan"
        )
    for (host_alias, hostname), actual in zip(HOSTS_V1, hosts, strict=True):
        if (
            actual.get("host_alias") != host_alias
            or actual.get("expected_hostname") != hostname
            or actual.get("actual_hostname") != hostname
            or type(actual.get("scanned_path_count")) is not int
            or actual["scanned_path_count"] < 0
            or actual.get("match_count") != 0
            or actual.get("matches") != []
        ):
            raise LearnedResourceForecastAnalysisHistoryU005Error(
                "U005 host row is not an exact zero-hit scan"
            )
    return receipt


def _scan(
    *,
    protocol_path: Path,
    manifest_path: Path,
    output: Path,
    scan_root: Path = DEFAULT_SCAN_ROOT,
    scanner: HostScannerV1 | None = None,
) -> dict[str, Any]:
    protocol = validate_ratified_analysis_successor_protocol_v1(
        _read_object(protocol_path, "U005 protocol")
    )
    manifest = _read_object(manifest_path, "U005 manifest")
    prepare = _prepare_module()
    if manifest != prepare.build_launch_manifest_v1(protocol):
        raise LearnedResourceForecastAnalysisHistoryU005Error(
            "U005 manifest does not replay from its builder"
        )
    fixed = manifest["fixed_paths"]
    resolved_output = require_path_outside_repository_v1(
        repository=REPOSITORY, path=output, label="U005 authority receipt"
    )
    if (
        bound_clean_source_commit_v1(REPOSITORY) != protocol["source_commit"]
        or REPOSITORY.resolve() != Path(fixed["source_checkout"]).resolve()
        or protocol_path.resolve() != Path(fixed["protocol"]).resolve()
        or manifest_path.resolve() != Path(fixed["manifest"]).resolve()
        or resolved_output != Path(fixed["authority_scan_receipt"]).resolve()
        or scan_root.resolve() != DEFAULT_SCAN_ROOT.resolve()
    ):
        raise LearnedResourceForecastAnalysisHistoryU005Error(
            "U005 history source, paths, or scope changed"
        )
    request = _expected_request(protocol, manifest, scan_root)
    run = scanner or _ssh_host_scan
    hosts = []
    for host_alias, expected_hostname in HOSTS_V1:
        result = run(host_alias, request)
        hosts.append(
            {
                "host_alias": host_alias,
                "expected_hostname": expected_hostname,
                **result,
            }
        )
    receipt = {
        "schema": SCHEMA_V1,
        "protocol_id": protocol["protocol_id"],
        "source_commit": protocol["source_commit"],
        "pilot_execution_identity": protocol["pilot_execution_identity"],
        "analysis_execution_id": protocol["analysis_execution_id"],
        "scan_root": request["scan_root"],
        "excluded_roots": request["excluded_roots"],
        "scanned_identity_tokens": request["execution_ids"],
        "new_training_execution_ids": [],
        "new_evidence_execution_ids": [],
        "new_tape_roots": [],
        "campaign_artifact_paths": request["campaign_artifact_paths"],
        "predecessor_authority_tokens_scanned_as_collisions": False,
        "hosts": hosts,
        "total_match_count": sum(row.get("match_count", -1) for row in hosts),
    }
    receipt["no_prior_identity_hits"] = receipt["total_match_count"] == 0
    write_exclusive_bytes_v1(resolved_output, canonical_json_bytes(receipt))
    if receipt["no_prior_identity_hits"]:
        validate_authority_scan_receipt_v1(receipt, protocol, manifest)
    return receipt


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--scan-root", type=Path, default=DEFAULT_SCAN_ROOT)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--host-scan-only", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = _arguments()
    try:
        if args.host_scan_only:
            protocol = validate_ratified_analysis_successor_protocol_v1(
                _read_object(args.protocol, "U005 protocol")
            )
            manifest = _read_object(args.manifest, "U005 manifest")
            if manifest != _prepare_module().build_launch_manifest_v1(protocol):
                raise LearnedResourceForecastAnalysisHistoryU005Error(
                    "U005 manifest does not replay"
                )
            print(
                json.dumps(
                    _scan_local_host(
                        _expected_request(protocol, manifest, args.scan_root)
                    ),
                    sort_keys=True,
                )
            )
            return 0
        if args.output is None:
            raise LearnedResourceForecastAnalysisHistoryU005Error(
                "central U005 scan requires the fixed output"
            )
        receipt = _scan(
            protocol_path=args.protocol,
            manifest_path=args.manifest,
            output=args.output,
            scan_root=args.scan_root,
        )
    except (
        LearnedResourceForecastAnalysisHistoryU005Error,
        LearnedResourceForecastAnalysisSuccessorProtocolV1Error,
        ScienceExecutionIOV1Error,
    ) as error:
        raise SystemExit(str(error)) from error
    print(json.dumps(receipt, sort_keys=True))
    return 0 if receipt["no_prior_identity_hits"] else 2


if __name__ == "__main__":
    sys.exit(main())
