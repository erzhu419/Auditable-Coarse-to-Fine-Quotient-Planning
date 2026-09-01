#!/usr/bin/env python3
"""Write the one-shot three-host prior-identity scan receipt for U001."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
from pathlib import Path
import platform
import re
import shlex
import subprocess
import sys
import tempfile
from typing import Any, Callable

from acfqp.phase3e_ids import canonical_json_bytes
from acfqp.science.execution_io_v1 import (
    ScienceExecutionIOV1Error,
    bound_clean_source_commit_v1,
    require_path_outside_repository_v1,
    write_exclusive_bytes_v1,
)
from acfqp.science.learned_resource_forecast_protocol_v1 import (
    LearnedResourceForecastProtocolV1Error,
    validate_ratified_learned_resource_forecast_protocol_v1,
)


REPOSITORY = Path(__file__).resolve().parents[1]
SCHEMA_V1 = "acfqp.science.learned_resource_forecast_history_scan_receipt.v1"
DEFAULT_SCAN_ROOT = Path("/home/erzhu419/mine_code")
TEXT_SUFFIXES_V1 = frozenset(
    {
        "",
        ".csv",
        ".json",
        ".jsonl",
        ".log",
        ".md",
        ".py",
        ".sh",
        ".toml",
        ".tsv",
        ".txt",
        ".yaml",
        ".yml",
    }
)
HostScannerV1 = Callable[[str, dict[str, Any]], dict[str, Any]]


class LearnedResourceForecastHistoryScanV1Error(RuntimeError):
    """The fixed three-host history scan or its receipt is not exact."""


def _load_prepare_module():
    path = REPOSITORY / "scripts/prepare_learned_resource_forecast_campaign_u001.py"
    spec = importlib.util.spec_from_file_location("acfqp_u001_prepare_for_scan", path)
    if spec is None or spec.loader is None:
        raise LearnedResourceForecastHistoryScanV1Error(
            "cannot load the U001 launch-manifest authority"
        )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _read_object(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise LearnedResourceForecastHistoryScanV1Error(
            f"cannot read {label} as one JSON object: {path}"
        ) from error
    if type(value) is not dict:
        raise LearnedResourceForecastHistoryScanV1Error(
            f"{label} must contain one JSON object"
        )
    return value


def _identity_roster(
    protocol: dict[str, Any], manifest: dict[str, Any]
) -> tuple[str, list[str], list[int]]:
    pilot_identity = protocol["pilot_execution_identity"]
    execution_ids = [
        job["execution_id"]
        for worker in manifest["workers"]
        for roster in ("policy_training_jobs", "player_evidence_jobs")
        for job in worker[roster]
    ]
    seeds = sorted(
        {seed for worker in manifest["workers"] for seed in worker["seeds"]}
    )
    if (
        pilot_identity != manifest["pilot_execution_identity"]
        or len(execution_ids) != 576
        or len(set(execution_ids)) != 576
        or len(seeds) != 48
    ):
        raise LearnedResourceForecastHistoryScanV1Error(
            "history-scan identity roster does not close the manifest"
        )
    return pilot_identity, execution_ids, seeds


def _host_roster(manifest: dict[str, Any]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    seen: set[str] = set()
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
        raise LearnedResourceForecastHistoryScanV1Error(
            "history scan no longer has exactly three execution hosts"
        )
    return rows


def _is_excluded(path: Path, exclusions: tuple[Path, ...]) -> bool:
    resolved = path.resolve()
    return any(resolved == root or root in resolved.parents for root in exclusions)


def _scan_text_file(
    path: Path,
    *,
    pilot_identity: str,
    execution_ids: tuple[str, ...],
    tape_roots: tuple[str, ...],
    campaign_artifact_paths: tuple[str, ...],
) -> tuple[set[str], set[str], set[str], bool]:
    execution_hits: set[str] = set()
    tape_hits: set[str] = set()
    path_hits: set[str] = set()
    pilot_hit = False
    try:
        with path.open("r", encoding="utf-8", errors="ignore") as stream:
            for line in stream:
                if pilot_identity in line:
                    pilot_hit = True
                execution_hits.update(
                    identity for identity in execution_ids if identity in line
                )
                tape_hits.update(value for value in tape_roots if value in line)
                path_hits.update(
                    value for value in campaign_artifact_paths if value in line
                )
    except OSError as error:
        raise LearnedResourceForecastHistoryScanV1Error(
            f"cannot scan supported history file: {path}"
        ) from error
    return execution_hits, tape_hits, path_hits, pilot_hit


def _scan_local_host(request: dict[str, Any]) -> dict[str, Any]:
    scan_root = Path(request["scan_root"]).resolve()
    exclusions = tuple(Path(value).resolve() for value in request["excluded_roots"])
    pilot_identity = request["pilot_execution_identity"]
    execution_ids = tuple(request["execution_ids"])
    tape_roots = tuple(request["tape_roots"])
    campaign_artifact_paths = tuple(request["campaign_artifact_paths"])
    if not scan_root.is_dir():
        raise LearnedResourceForecastHistoryScanV1Error(
            "history scan root is not a directory"
        )
    matches: set[tuple[str, str, str]] = set()
    scanned_path_count = 0
    for directory, dirnames, filenames in os.walk(scan_root, topdown=True):
        directory_path = Path(directory)
        dirnames[:] = [
            name
            for name in dirnames
            if not _is_excluded(directory_path / name, exclusions)
        ]
        for name in (*dirnames, *filenames):
            path = directory_path / name
            if _is_excluded(path, exclusions):
                continue
            scanned_path_count += 1
            path_text = str(path)
            if pilot_identity in path_text:
                matches.add((path_text, "pilot_execution_identity", pilot_identity))
                for identity in execution_ids:
                    if identity in path_text:
                        matches.add((path_text, "execution_id", identity))
            for value in tape_roots:
                if value in path_text:
                    matches.add((path_text, "frozen_tape_root", value))
            for value in campaign_artifact_paths:
                if value in path_text:
                    matches.add(
                        (path_text, "fixed_campaign_artifact_path", value)
                    )
    regex_rows = [re.escape(pilot_identity)]
    regex_rows.extend(re.escape(identity) for identity in execution_ids)
    regex_rows.extend(re.escape(value) for value in tape_roots)
    regex_rows.extend(re.escape(value) for value in campaign_artifact_paths)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", prefix="acfqp-u001-history-", suffix=".patterns"
    ) as pattern_file:
        pattern_file.write("\n".join(regex_rows) + "\n")
        pattern_file.flush()
        command = [
            "rg",
            "--no-messages",
            "--files-with-matches",
            "--regexp",
            "",
            "--file",
            pattern_file.name,
        ]
        command[3:5] = []
        for suffix in sorted(TEXT_SUFFIXES_V1 - {""}):
            command.extend(["--glob", f"*{suffix}"])
        for excluded in exclusions:
            try:
                relative = excluded.relative_to(scan_root)
            except ValueError:
                continue
            command.extend(["--glob", f"!{relative.as_posix()}/**"])
        command.append(str(scan_root))
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
        )
    if completed.returncode not in (0, 1):
        raise LearnedResourceForecastHistoryScanV1Error(
            f"ripgrep history scan failed: {completed.stderr.strip()}"
        )
    for value in completed.stdout.splitlines():
        path = Path(value)
        if not path.is_absolute():
            path = scan_root / path
        if _is_excluded(path, exclusions) or not path.is_file():
            continue
        path_text = str(path)
        execution_hits, tape_hits, path_hits, pilot_hit = _scan_text_file(
            path,
            pilot_identity=pilot_identity,
            execution_ids=execution_ids,
            tape_roots=tape_roots,
            campaign_artifact_paths=campaign_artifact_paths,
        )
        if pilot_hit:
            matches.add((path_text, "pilot_execution_identity", pilot_identity))
        matches.update((path_text, "execution_id", value) for value in execution_hits)
        matches.update((path_text, "frozen_tape_root", value) for value in tape_hits)
        matches.update(
            (path_text, "fixed_campaign_artifact_path", value)
            for value in path_hits
        )
    records = [
        {"path": path, "identity_kind": kind, "identity": identity}
        for path, kind, identity in sorted(matches)
    ]
    return {
        "actual_hostname": platform.node(),
        "scanned_path_count": scanned_path_count,
        "match_count": len(records),
        "matches": records,
    }


def _ssh_host_scan(host_alias: str, request: dict[str, Any]) -> dict[str, Any]:
    script = REPOSITORY / "scripts/scan_learned_resource_forecast_history_u001.py"
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
        ["ssh", "-o", "BatchMode=yes", host_alias, command],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise LearnedResourceForecastHistoryScanV1Error(
            f"history scan failed on {host_alias}: {completed.stderr.strip()}"
        )
    try:
        result = json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        raise LearnedResourceForecastHistoryScanV1Error(
            f"history scan on {host_alias} returned no exact JSON result"
        ) from error
    if type(result) is not dict:
        raise LearnedResourceForecastHistoryScanV1Error(
            f"history scan on {host_alias} returned a non-object"
        )
    return result


def _expected_scan_request(
    protocol: dict[str, Any], manifest: dict[str, Any], scan_root: Path
) -> dict[str, Any]:
    pilot_identity, execution_ids, seeds = _identity_roster(protocol, manifest)
    fixed = manifest["fixed_paths"]
    history_contract = manifest["history_scan_contract"]
    return {
        "protocol": fixed["protocol"],
        "manifest": fixed["manifest"],
        "source_pythonpath": fixed["source_pythonpath"],
        "scan_root": str(scan_root.resolve()),
        "excluded_roots": [fixed["source_checkout"], fixed["launch_root"]],
        "pilot_execution_identity": pilot_identity,
        "execution_ids": execution_ids,
        "seeds": seeds,
        "tape_roots": history_contract["frozen_tape_roots"],
        "campaign_artifact_paths": history_contract[
            "fixed_campaign_artifact_paths"
        ],
    }


def validate_history_scan_receipt_v1(
    receipt: dict[str, Any], protocol: dict[str, Any], manifest: dict[str, Any]
) -> dict[str, Any]:
    request = _expected_scan_request(protocol, manifest, DEFAULT_SCAN_ROOT)
    expected_hosts = _host_roster(manifest)
    host_rows = receipt.get("hosts")
    if (
        receipt.get("schema") != SCHEMA_V1
        or receipt.get("protocol_id") != protocol["protocol_id"]
        or receipt.get("source_commit") != protocol["source_commit"]
        or receipt.get("pilot_execution_identity")
        != request["pilot_execution_identity"]
        or receipt.get("scan_root") != request["scan_root"]
        or receipt.get("excluded_roots") != request["excluded_roots"]
        or receipt.get("execution_ids") != request["execution_ids"]
        or receipt.get("seeds") != request["seeds"]
        or receipt.get("tape_roots") != request["tape_roots"]
        or receipt.get("campaign_artifact_paths")
        != request["campaign_artifact_paths"]
        or receipt.get("bare_seed_global_match_is_execution_identity") is not False
        or type(host_rows) is not list
        or len(host_rows) != 3
        or receipt.get("total_match_count") != 0
        or receipt.get("no_prior_identity_hits") is not True
    ):
        raise LearnedResourceForecastHistoryScanV1Error(
            "history-scan receipt does not bind the exact zero-hit identity roster"
        )
    for expected, actual in zip(expected_hosts, host_rows, strict=True):
        if (
            actual.get("host_alias") != expected["host_alias"]
            or actual.get("expected_hostname") != expected["expected_hostname"]
            or actual.get("actual_hostname") != expected["expected_hostname"]
            or type(actual.get("scanned_path_count")) is not int
            or actual["scanned_path_count"] < 0
            or actual.get("match_count") != 0
            or actual.get("matches") != []
        ):
            raise LearnedResourceForecastHistoryScanV1Error(
                "history-scan host row is not an exact successful zero-hit scan"
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
    protocol = validate_ratified_learned_resource_forecast_protocol_v1(
        _read_object(protocol_path, "ratified U001 protocol")
    )
    manifest = _read_object(manifest_path, "U001 launch manifest")
    prepare = _load_prepare_module()
    if manifest != prepare.build_launch_manifest_v1(protocol):
        raise LearnedResourceForecastHistoryScanV1Error(
            "launch manifest does not replay from the ratified protocol"
        )
    fixed = manifest["fixed_paths"]
    resolved_output = require_path_outside_repository_v1(
        repository=REPOSITORY, path=output, label="U001 history-scan receipt"
    )
    if (
        source_commit != protocol["source_commit"]
        or Path(protocol_path).resolve() != Path(fixed["protocol"]).resolve()
        or Path(manifest_path).resolve() != Path(fixed["manifest"]).resolve()
        or resolved_output != Path(fixed["history_scan_receipt"]).resolve()
        or scan_root.resolve() != DEFAULT_SCAN_ROOT.resolve()
    ):
        raise LearnedResourceForecastHistoryScanV1Error(
            "history scan differs from the fixed source, inputs, output, or scope"
        )
    request = _expected_scan_request(protocol, manifest, scan_root)
    run_host_scan = scanner or _ssh_host_scan
    hosts = []
    for expected in _host_roster(manifest):
        host_request = {**request, "python": expected["python"]}
        result = run_host_scan(expected["host_alias"], host_request)
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
        "seeds": request["seeds"],
        "tape_roots": request["tape_roots"],
        "campaign_artifact_paths": request["campaign_artifact_paths"],
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
            protocol = validate_ratified_learned_resource_forecast_protocol_v1(
                _read_object(args.protocol, "ratified U001 protocol")
            )
            manifest = _read_object(args.manifest, "U001 launch manifest")
            prepare = _load_prepare_module()
            if manifest != prepare.build_launch_manifest_v1(protocol):
                raise LearnedResourceForecastHistoryScanV1Error(
                    "launch manifest does not replay from the ratified protocol"
                )
            request = _expected_scan_request(protocol, manifest, args.scan_root)
            print(json.dumps(_scan_local_host(request), sort_keys=True))
            return 0
        if args.output is None:
            raise LearnedResourceForecastHistoryScanV1Error(
                "central history scan requires its fixed output path"
            )
        receipt = _scan(
            protocol_path=args.protocol,
            manifest_path=args.manifest,
            output=args.output,
            scan_root=args.scan_root,
        )
    except (
        LearnedResourceForecastHistoryScanV1Error,
        LearnedResourceForecastProtocolV1Error,
        ScienceExecutionIOV1Error,
    ) as error:
        raise SystemExit(str(error)) from error
    print(json.dumps(receipt, sort_keys=True))
    return 0 if receipt["no_prior_identity_hits"] else 2


if __name__ == "__main__":
    sys.exit(main())
