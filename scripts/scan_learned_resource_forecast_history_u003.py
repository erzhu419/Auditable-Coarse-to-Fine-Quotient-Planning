#!/usr/bin/env python3
"""Write the one-shot three-host fresh-identity scan receipt for U003."""

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
from acfqp.science.learned_resource_forecast_evidence_successor_protocol_v1 import (
    LearnedResourceForecastEvidenceSuccessorProtocolV1Error,
    validate_ratified_learned_resource_forecast_evidence_successor_protocol_v1,
)


REPOSITORY = Path(__file__).resolve().parents[1]
SCHEMA_V1 = (
    "acfqp.science.learned_resource_forecast_evidence_successor_history_scan.v1"
)
DEFAULT_SCAN_ROOT = Path("/home/erzhu419/mine_code")
HostScannerV1 = Callable[[str, dict[str, Any]], dict[str, Any]]
SSH_NO_MUX_OPTIONS_V1 = (
    "-o",
    "BatchMode=yes",
    "-o",
    "ControlMaster=no",
    "-o",
    "ControlPath=none",
)


class LearnedResourceForecastEvidenceSuccessorHistoryScanV1Error(RuntimeError):
    """The exact fresh U003 history scan or receipt is not exact."""


def _load_script(name: str, filename: str):
    path = REPOSITORY / "scripts" / filename
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise LearnedResourceForecastEvidenceSuccessorHistoryScanV1Error(
            f"cannot load history-scan dependency: {path}"
        )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _prepare_module():
    return _load_script(
        "acfqp_u003_prepare_for_history",
        "prepare_learned_resource_forecast_evidence_successor_u003.py",
    )


def _base_scan_module():
    return _load_script(
        "acfqp_u002_history_scan_engine_for_u003",
        "scan_learned_resource_forecast_history_u002.py",
    )


def _read_object(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise LearnedResourceForecastEvidenceSuccessorHistoryScanV1Error(
            f"cannot read {label}: {path}"
        ) from error
    if type(value) is not dict:
        raise LearnedResourceForecastEvidenceSuccessorHistoryScanV1Error(
            f"{label} must contain one JSON object"
        )
    return value


def _identity_roster(
    protocol: dict[str, Any], manifest: dict[str, Any]
) -> tuple[str, list[str], list[int]]:
    execution_ids = [
        job["execution_id"]
        for worker in manifest["workers"]
        for job in worker["player_evidence_jobs"]
    ]
    seeds = sorted(seed for worker in manifest["workers"] for seed in worker["seeds"])
    if (
        manifest["pilot_execution_identity"] != protocol["pilot_execution_identity"]
        or len(execution_ids) != 432
        or len(set(execution_ids)) != 432
        or len(seeds) != 48
        or len(set(seeds)) != 48
    ):
        raise LearnedResourceForecastEvidenceSuccessorHistoryScanV1Error(
            "U003 history-scan identity roster does not close 432 fresh jobs"
        )
    return protocol["pilot_execution_identity"], execution_ids, seeds


def _host_roster(manifest: dict[str, Any]) -> list[dict[str, str]]:
    rows = []
    seen = set()
    for worker in manifest["workers"]:
        if worker["host_alias"] in seen:
            continue
        seen.add(worker["host_alias"])
        rows.append(
            {
                "host_alias": worker["host_alias"],
                "expected_hostname": worker["expected_hostname"],
                "python": worker["python"],
            }
        )
    if len(rows) != 3:
        raise LearnedResourceForecastEvidenceSuccessorHistoryScanV1Error(
            "U003 history scan no longer has exactly three hosts"
        )
    return rows


def _expected_scan_request(
    protocol: dict[str, Any], manifest: dict[str, Any], scan_root: Path
) -> dict[str, Any]:
    identity, execution_ids, seeds = _identity_roster(protocol, manifest)
    fixed = manifest["fixed_paths"]
    contract = manifest["history_scan_contract"]
    return {
        "protocol": fixed["protocol"],
        "manifest": fixed["manifest"],
        "source_pythonpath": fixed["source_pythonpath"],
        "scan_root": str(scan_root.resolve()),
        "excluded_roots": [fixed["source_checkout"], fixed["launch_root"]],
        "pilot_execution_identity": identity,
        "execution_ids": execution_ids,
        "seeds": seeds,
        "tape_roots": contract["fresh_tape_roots"],
        "campaign_artifact_paths": contract["fresh_campaign_artifact_paths"],
    }


def _scan_local_host(request: dict[str, Any]) -> dict[str, Any]:
    base = _base_scan_module()
    try:
        return base._scan_local_host(request)
    except base.LearnedResourceForecastHistoryScanV1Error as error:
        raise LearnedResourceForecastEvidenceSuccessorHistoryScanV1Error(
            str(error)
        ) from error


def _ssh_host_scan(host_alias: str, request: dict[str, Any]) -> dict[str, Any]:
    command = shlex.join(
        [
            "env",
            f"PYTHONPATH={request['source_pythonpath']}",
            request["python"],
            str(REPOSITORY / "scripts/scan_learned_resource_forecast_history_u003.py"),
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
        raise LearnedResourceForecastEvidenceSuccessorHistoryScanV1Error(
            f"U003 history scan failed on {host_alias}: {completed.stderr.strip()}"
        )
    try:
        result = json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        raise LearnedResourceForecastEvidenceSuccessorHistoryScanV1Error(
            f"U003 history scan on {host_alias} returned no JSON"
        ) from error
    if type(result) is not dict:
        raise LearnedResourceForecastEvidenceSuccessorHistoryScanV1Error(
            "U003 history scan returned non-object"
        )
    return result


def validate_history_scan_receipt_v1(
    receipt: dict[str, Any], protocol: dict[str, Any], manifest: dict[str, Any]
) -> dict[str, Any]:
    request = _expected_scan_request(protocol, manifest, DEFAULT_SCAN_ROOT)
    host_rows = receipt.get("hosts")
    if (
        receipt.get("schema") != SCHEMA_V1
        or receipt.get("protocol_id") != protocol["protocol_id"]
        or receipt.get("source_commit") != protocol["source_commit"]
        or receipt.get("pilot_execution_identity")
        != protocol["pilot_execution_identity"]
        or receipt.get("scan_root") != request["scan_root"]
        or receipt.get("excluded_roots") != request["excluded_roots"]
        or receipt.get("execution_ids") != request["execution_ids"]
        or receipt.get("execution_id_count") != 432
        or receipt.get("seeds") != request["seeds"]
        or receipt.get("tape_roots") != request["tape_roots"]
        or receipt.get("campaign_artifact_paths")
        != request["campaign_artifact_paths"]
        or receipt.get("predecessor_authority_tokens_scanned_as_collisions")
        is not False
        or receipt.get("bare_seed_global_match_is_execution_identity") is not False
        or type(host_rows) is not list
        or len(host_rows) != 3
        or receipt.get("total_match_count") != 0
        or receipt.get("no_prior_identity_hits") is not True
    ):
        raise LearnedResourceForecastEvidenceSuccessorHistoryScanV1Error(
            "U003 history receipt does not bind exact fresh zero-hit roster"
        )
    for expected, actual in zip(_host_roster(manifest), host_rows, strict=True):
        if (
            actual.get("host_alias") != expected["host_alias"]
            or actual.get("expected_hostname") != expected["expected_hostname"]
            or actual.get("actual_hostname") != expected["expected_hostname"]
            or type(actual.get("scanned_path_count")) is not int
            or actual["scanned_path_count"] < 0
            or actual.get("match_count") != 0
            or actual.get("matches") != []
        ):
            raise LearnedResourceForecastEvidenceSuccessorHistoryScanV1Error(
                "U003 history host row is not exact zero-hit scan"
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
    source_commit = bound_clean_source_commit_v1(REPOSITORY)
    protocol = (
        validate_ratified_learned_resource_forecast_evidence_successor_protocol_v1(
            _read_object(protocol_path, "U003 protocol")
        )
    )
    manifest = _read_object(manifest_path, "U003 manifest")
    if manifest != _prepare_module().build_launch_manifest_v1(protocol):
        raise LearnedResourceForecastEvidenceSuccessorHistoryScanV1Error(
            "U003 manifest does not replay from exact builder"
        )
    fixed = manifest["fixed_paths"]
    resolved_output = require_path_outside_repository_v1(
        repository=REPOSITORY, path=output, label="U003 history receipt"
    )
    if (
        source_commit != protocol["source_commit"]
        or Path(protocol_path).resolve() != Path(fixed["protocol"]).resolve()
        or Path(manifest_path).resolve() != Path(fixed["manifest"]).resolve()
        or resolved_output != Path(fixed["history_scan_receipt"]).resolve()
        or scan_root.resolve() != DEFAULT_SCAN_ROOT.resolve()
    ):
        raise LearnedResourceForecastEvidenceSuccessorHistoryScanV1Error(
            "U003 history scan source, paths, or scope changed"
        )
    request = _expected_scan_request(protocol, manifest, scan_root)
    run = scanner or _ssh_host_scan
    hosts = []
    for expected in _host_roster(manifest):
        result = run(
            expected["host_alias"], {**request, "python": expected["python"]}
        )
        hosts.append(
            {
                "host_alias": expected["host_alias"],
                "expected_hostname": expected["expected_hostname"],
                **result,
            }
        )
    receipt = {
        "schema": SCHEMA_V1,
        "protocol_id": protocol["protocol_id"],
        "source_commit": protocol["source_commit"],
        "pilot_execution_identity": request["pilot_execution_identity"],
        "scan_root": request["scan_root"],
        "excluded_roots": request["excluded_roots"],
        "execution_ids": request["execution_ids"],
        "execution_id_count": len(request["execution_ids"]),
        "seeds": request["seeds"],
        "tape_roots": request["tape_roots"],
        "campaign_artifact_paths": request["campaign_artifact_paths"],
        "predecessor_authority_tokens_scanned_as_collisions": False,
        "bare_seed_global_match_is_execution_identity": False,
        "hosts": hosts,
        "total_match_count": sum(row.get("match_count", -1) for row in hosts),
    }
    receipt["no_prior_identity_hits"] = receipt["total_match_count"] == 0
    write_exclusive_bytes_v1(resolved_output, canonical_json_bytes(receipt))
    if receipt["no_prior_identity_hits"]:
        validate_history_scan_receipt_v1(receipt, protocol, manifest)
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
            protocol = validate_ratified_learned_resource_forecast_evidence_successor_protocol_v1(
                _read_object(args.protocol, "U003 protocol")
            )
            manifest = _read_object(args.manifest, "U003 manifest")
            if manifest != _prepare_module().build_launch_manifest_v1(protocol):
                raise LearnedResourceForecastEvidenceSuccessorHistoryScanV1Error(
                    "U003 manifest does not replay"
                )
            print(
                json.dumps(
                    _scan_local_host(
                        _expected_scan_request(protocol, manifest, args.scan_root)
                    ),
                    sort_keys=True,
                )
            )
            return 0
        if args.output is None:
            raise LearnedResourceForecastEvidenceSuccessorHistoryScanV1Error(
                "central U003 history scan requires fixed output"
            )
        receipt = _scan(
            protocol_path=args.protocol,
            manifest_path=args.manifest,
            output=args.output,
            scan_root=args.scan_root,
        )
    except (
        LearnedResourceForecastEvidenceSuccessorHistoryScanV1Error,
        LearnedResourceForecastEvidenceSuccessorProtocolV1Error,
        ScienceExecutionIOV1Error,
    ) as error:
        raise SystemExit(str(error)) from error
    print(json.dumps(receipt, sort_keys=True))
    return 0 if receipt["no_prior_identity_hits"] else 2


if __name__ == "__main__":
    sys.exit(main())
