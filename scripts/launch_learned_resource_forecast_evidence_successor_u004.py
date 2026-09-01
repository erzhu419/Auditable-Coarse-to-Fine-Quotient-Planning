#!/usr/bin/env python3
"""Durably dispatch the six fresh U004 evidence workers exactly once."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
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
)
from acfqp.science.learned_resource_forecast_evidence_successor_protocol_v1 import (
    U002_PROTOCOL_ID_V1,
    LearnedResourceForecastEvidenceSuccessorProtocolV1Error,
    validate_ratified_learned_resource_forecast_evidence_successor_protocol_v1,
)
from acfqp.science.learned_resource_forecast_protocol_v1 import (
    validate_ratified_learned_resource_forecast_protocol_v1,
)


REPOSITORY = Path(__file__).resolve().parents[1]
WORKER_SCRIPT_NAME_V1 = "run_learned_resource_forecast_worker_u004.py"
DispatcherV1 = Callable[[str, str], str]
GlobalPreflightV1 = Callable[[str, str], dict[str, Any]]
SSH_NO_MUX_OPTIONS_V1 = (
    "-o",
    "BatchMode=yes",
    "-o",
    "ControlMaster=no",
    "-o",
    "ControlPath=none",
)


class LearnedResourceForecastEvidenceSuccessorLauncherV1Error(RuntimeError):
    """One U004 preflight, one-shot dispatch, or parent binding failed."""


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=("evidence",), default="evidence")
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--history-scan-receipt", type=Path, required=True)
    parser.add_argument("--remote-results-root", type=Path, required=True)
    parser.add_argument("--remote-status-root", type=Path, required=True)
    parser.add_argument("--remote-log-root", type=Path, required=True)
    parser.add_argument("--dispatch-status", type=Path, required=True)
    return parser.parse_args()


def _read_object(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise LearnedResourceForecastEvidenceSuccessorLauncherV1Error(
            f"cannot read {label}: {path}"
        ) from error
    if type(value) is not dict:
        raise LearnedResourceForecastEvidenceSuccessorLauncherV1Error(
            f"{label} must contain one JSON object"
        )
    return value


def _read_jsonl(path: Path, label: str) -> list[dict[str, Any]]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as error:
        raise LearnedResourceForecastEvidenceSuccessorLauncherV1Error(
            f"cannot read {label}: {path}"
        ) from error
    rows = []
    for line in lines:
        try:
            row = json.loads(line)
        except json.JSONDecodeError as error:
            raise LearnedResourceForecastEvidenceSuccessorLauncherV1Error(
                f"{label} contains malformed JSONL"
            ) from error
        if type(row) is not dict:
            raise LearnedResourceForecastEvidenceSuccessorLauncherV1Error(
                f"{label} contains non-object row"
            )
        rows.append(row)
    if not rows:
        raise LearnedResourceForecastEvidenceSuccessorLauncherV1Error(
            f"{label} is empty"
        )
    return rows


def _load_script(name: str, filename: str):
    path = REPOSITORY / "scripts" / filename
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise LearnedResourceForecastEvidenceSuccessorLauncherV1Error(
            f"cannot load launcher dependency: {path}"
        )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _DispatchStatusV1:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._fd: int | None = None

    def __enter__(self) -> "_DispatchStatusV1":
        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self._fd = os.open(
                self.path,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC,
                0o600,
            )
        except FileExistsError as error:
            raise LearnedResourceForecastEvidenceSuccessorLauncherV1Error(
                "U004 dispatch status exists; launch identity is consumed"
            ) from error
        return self

    def emit(self, event: dict[str, Any]) -> None:
        if self._fd is None:
            raise LearnedResourceForecastEvidenceSuccessorLauncherV1Error(
                "dispatch stream is not open"
            )
        view = memoryview(canonical_json_bytes(event) + b"\n")
        while view:
            view = view[os.write(self._fd, view) :]
        os.fsync(self._fd)

    def __exit__(self, _type, _value, _traceback) -> None:
        if self._fd is not None:
            os.close(self._fd)
            self._fd = None


def _process_arguments(
    *,
    worker: dict[str, Any],
    protocol_path: Path,
    manifest_path: Path,
    source_checkout: Path,
    source_pythonpath: Path,
    results_root: Path,
    status_root: Path,
) -> list[str]:
    return [
        "env",
        f"PYTHONPATH={source_pythonpath}",
        worker["python"],
        str(source_checkout / "scripts" / WORKER_SCRIPT_NAME_V1),
        "--worker",
        str(worker["worker"]),
        "--phase",
        "evidence",
        "--protocol",
        str(protocol_path),
        "--manifest",
        str(manifest_path),
        "--predecessor-protocol",
        worker["_fixed_predecessor_protocol"],
        "--predecessor-manifest",
        worker["_fixed_predecessor_manifest"],
        "--predecessor-results-root",
        worker["predecessor_snapshot_root"],
        "--results-root",
        str(results_root / f"worker-{worker['worker']}"),
        "--status-stream",
        str(status_root / worker["player_evidence_status_stream"]),
        "--device",
        worker["device"],
    ]


def _remote_global_preflight_command(
    *,
    worker: dict[str, Any],
    protocol_path: Path,
    manifest_path: Path,
    source_checkout: Path,
    source_pythonpath: Path,
    results_root: Path,
    status_root: Path,
    log_root: Path,
) -> str:
    process = _process_arguments(
        worker=worker,
        protocol_path=protocol_path,
        manifest_path=manifest_path,
        source_checkout=source_checkout,
        source_pythonpath=source_pythonpath,
        results_root=results_root,
        status_root=status_root,
    )
    status_path = status_root / worker["player_evidence_status_stream"]
    log_path = log_root / f"worker-{worker['worker']}-evidence.log"
    checks = [
        "set -eu",
        f"test -x {shlex.quote(worker['python'])}",
        f"test -f {shlex.quote(str(source_checkout / 'scripts' / WORKER_SCRIPT_NAME_V1))}",
        f"test -d {shlex.quote(str(source_pythonpath))}",
        f"test -f {shlex.quote(str(protocol_path))}",
        f"test -f {shlex.quote(str(manifest_path))}",
        f"test ! -e {shlex.quote(str(status_path))}",
        f"test ! -e {shlex.quote(str(log_path))}",
        shlex.join([*process, "--global-preflight-only"]),
    ]
    command = "; ".join(checks)
    if "mkdir" in command or "nohup" in command or ">" in command:
        raise AssertionError("U004 global preflight stopped being read-only")
    return command


def _remote_worker_command(
    *,
    worker: dict[str, Any],
    protocol_path: Path,
    manifest_path: Path,
    source_checkout: Path,
    source_pythonpath: Path,
    results_root: Path,
    status_root: Path,
    log_root: Path,
    first_worker_for_host: bool,
) -> tuple[str, Path, Path, Path]:
    worker_root = results_root / f"worker-{worker['worker']}"
    status_path = status_root / worker["player_evidence_status_stream"]
    log_path = log_root / f"worker-{worker['worker']}-evidence.log"
    process = _process_arguments(
        worker=worker,
        protocol_path=protocol_path,
        manifest_path=manifest_path,
        source_checkout=source_checkout,
        source_pythonpath=source_pythonpath,
        results_root=results_root,
        status_root=status_root,
    )
    setup = [
        "set -eu",
        "umask 077",
        f"test -x {shlex.quote(worker['python'])}",
        f"test -f {shlex.quote(str(source_checkout / 'scripts' / WORKER_SCRIPT_NAME_V1))}",
        f"test -f {shlex.quote(str(protocol_path))}",
        f"test -f {shlex.quote(str(manifest_path))}",
        f"test ! -e {shlex.quote(str(status_path))}",
        f"test ! -e {shlex.quote(str(log_path))}",
    ]
    if first_worker_for_host:
        setup.extend(
            [
                f"test ! -e {shlex.quote(str(results_root))}",
                f"test ! -e {shlex.quote(str(status_root))}",
                f"test ! -e {shlex.quote(str(log_root))}",
                f"mkdir {shlex.quote(str(results_root))} {shlex.quote(str(status_root))} {shlex.quote(str(log_root))}",
            ]
        )
    else:
        setup.extend(
            [
                f"test -d {shlex.quote(str(results_root))}",
                f"test -d {shlex.quote(str(status_root))}",
                f"test -d {shlex.quote(str(log_root))}",
            ]
        )
    setup.extend(
        [
            f"test ! -e {shlex.quote(str(worker_root))}",
            f"mkdir {shlex.quote(str(worker_root))}",
        ]
    )
    launch = (
        f"{shlex.join([*process, '--preflight-only'])} > /dev/null; "
        f"nohup {shlex.join(process)} > {shlex.quote(str(log_path))} "
        "2>&1 < /dev/null & worker_pid=$!; printf \"%s\\n\" \"$worker_pid\""
    )
    return "; ".join((*setup, launch)), worker_root, status_path, log_path


def _ssh_command(host_alias: str, remote_command: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["ssh", *SSH_NO_MUX_OPTIONS_V1, host_alias, remote_command],
        check=False,
        capture_output=True,
        text=True,
    )


def _ssh_dispatch(host_alias: str, remote_command: str) -> str:
    completed = _ssh_command(host_alias, remote_command)
    if completed.returncode != 0:
        raise LearnedResourceForecastEvidenceSuccessorLauncherV1Error(
            f"remote dispatch failed on {host_alias}: {completed.stderr.strip()}"
        )
    pid = completed.stdout.strip()
    if not pid.isdecimal() or int(pid) <= 0:
        raise LearnedResourceForecastEvidenceSuccessorLauncherV1Error(
            f"remote dispatch on {host_alias} returned no exact PID"
        )
    return pid


def _ssh_global_preflight(host_alias: str, remote_command: str) -> dict[str, Any]:
    completed = _ssh_command(host_alias, remote_command)
    if completed.returncode != 0:
        raise LearnedResourceForecastEvidenceSuccessorLauncherV1Error(
            f"global preflight failed on {host_alias}: {completed.stderr.strip()}"
        )
    try:
        value = json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        raise LearnedResourceForecastEvidenceSuccessorLauncherV1Error(
            f"global preflight on {host_alias} returned no JSON"
        ) from error
    if type(value) is not dict:
        raise LearnedResourceForecastEvidenceSuccessorLauncherV1Error(
            "global preflight returned non-object"
        )
    return value


def _validate_failed_u002_evidence_dispatch(path: Path) -> None:
    rows = _read_jsonl(path, "ineligible failed U002 evidence dispatch")
    events = [row.get("event") for row in rows]
    if (
        events != [
            "GLOBAL_PRECHECK_COMPLETED",
            "DISPATCH_STARTED",
            "WORKER_DISPATCH_FAILED",
            "DISPATCH_FAILED",
        ]
        or rows[2].get("phase") != "evidence"
        or rows[2].get("worker") != 0
        or rows[3].get("dispatched_worker_count") != 0
        or any(row.get("event") == "WORKER_DISPATCHED" for row in rows)
    ):
        raise LearnedResourceForecastEvidenceSuccessorLauncherV1Error(
            "U002 failed evidence-dispatch boundary is not exact 0-worker failure"
        )


def _launch(
    args: argparse.Namespace,
    *,
    dispatcher: DispatcherV1 | None = None,
    global_preflight: GlobalPreflightV1 | None = None,
) -> dict[str, Any]:
    def outside(path: Path, label: str) -> Path:
        return require_path_outside_repository_v1(
            repository=REPOSITORY, path=path, label=label
        )

    protocol_path = outside(args.protocol, "U004 protocol")
    manifest_path = outside(args.manifest, "U004 manifest")
    history_path = outside(args.history_scan_receipt, "U004 history receipt")
    results_root = outside(args.remote_results_root, "U004 results root")
    status_root = outside(args.remote_status_root, "U004 status root")
    log_root = outside(args.remote_log_root, "U004 log root")
    dispatch_path = outside(args.dispatch_status, "U004 dispatch status")
    source_commit = bound_clean_source_commit_v1(REPOSITORY)
    protocol = (
        validate_ratified_learned_resource_forecast_evidence_successor_protocol_v1(
            _read_object(protocol_path, "U004 protocol")
        )
    )
    prepare = _load_script(
        "acfqp_u004_prepare_for_launcher",
        "prepare_learned_resource_forecast_evidence_successor_u004.py",
    )
    manifest = _read_object(manifest_path, "U004 manifest")
    if manifest != prepare.build_launch_manifest_v1(protocol):
        raise LearnedResourceForecastEvidenceSuccessorLauncherV1Error(
            "U004 manifest does not replay from exact builder"
        )
    fixed = manifest["fixed_paths"]
    if (
        source_commit != protocol["source_commit"]
        or REPOSITORY.resolve() != Path(fixed["source_checkout"]).resolve()
        or protocol_path != Path(fixed["protocol"]).resolve()
        or manifest_path != Path(fixed["manifest"]).resolve()
        or history_path != Path(fixed["history_scan_receipt"]).resolve()
        or results_root != Path(fixed["results_root"]).resolve()
        or status_root != Path(fixed["status_root"]).resolve()
        or log_root != Path(fixed["log_root"]).resolve()
        or dispatch_path != Path(fixed["evidence_dispatch_status"]).resolve()
    ):
        raise LearnedResourceForecastEvidenceSuccessorLauncherV1Error(
            "U004 source, authority, or fixed output path changed"
        )
    history = _load_script(
        "acfqp_u004_history_for_launcher",
        "scan_learned_resource_forecast_history_u004.py",
    )
    history.validate_history_scan_receipt_v1(
        _read_object(history_path, "U004 history receipt"), protocol, manifest
    )
    predecessor_protocol = validate_ratified_learned_resource_forecast_protocol_v1(
        _read_object(Path(fixed["predecessor_protocol"]), "U002 protocol")
    )
    predecessor_manifest = _read_object(
        Path(fixed["predecessor_manifest"]), "U002 manifest"
    )
    u002_prepare = _load_script(
        "acfqp_u002_prepare_for_u004_launcher",
        "prepare_learned_resource_forecast_campaign_u002.py",
    )
    if (
        predecessor_protocol["protocol_id"] != U002_PROTOCOL_ID_V1
        or protocol["evaluation_tape_prefix"]
        != predecessor_protocol["evaluation_tape_prefix"]
        or protocol["predecessor_training_authority"][
            "model_evaluation_tape_prefix"
        ]
        != predecessor_protocol["evaluation_tape_prefix"]
        or protocol["predecessor_training_authority"][
            "model_evaluation_reexecuted_in_u004"
        ]
        is not False
        or predecessor_manifest
        != u002_prepare.build_launch_manifest_v1(predecessor_protocol)
    ):
        raise LearnedResourceForecastEvidenceSuccessorLauncherV1Error(
            "U002 predecessor protocol or manifest changed"
        )
    u002_postprocess = _load_script(
        "acfqp_u002_postprocess_for_u004_launcher",
        "postprocess_retain_learned_resource_forecast_u002.py",
    )
    u002_postprocess._validate_dispatch_status(
        Path(fixed["predecessor_training_dispatch_status"]),
        phase="training",
        manifest=predecessor_manifest,
        fixed=predecessor_manifest["fixed_paths"],
    )
    _validate_failed_u002_evidence_dispatch(
        Path(fixed["ineligible_predecessor_evidence_dispatch_status"])
    )
    if dispatch_path.exists():
        raise LearnedResourceForecastEvidenceSuccessorLauncherV1Error(
            "U004 evidence dispatch exists; launch identity is consumed"
        )
    source_checkout = Path(manifest["source_checkout"])
    source_pythonpath = Path(manifest["source_pythonpath"])
    workers = []
    for row in manifest["workers"]:
        workers.append(
            {
                **row,
                "_fixed_predecessor_protocol": fixed["predecessor_protocol"],
                "_fixed_predecessor_manifest": fixed["predecessor_manifest"],
            }
        )
    preflight = global_preflight or _ssh_global_preflight
    preflight_rows = []
    for worker in workers:
        row = preflight(
            worker["host_alias"],
            _remote_global_preflight_command(
                worker=worker,
                protocol_path=protocol_path,
                manifest_path=manifest_path,
                source_checkout=source_checkout,
                source_pythonpath=source_pythonpath,
                results_root=results_root,
                status_root=status_root,
                log_root=log_root,
            ),
        )
        if (
            row.get("success") is not True
            or row.get("global_preflight_only") is not True
            or row.get("phase") != "evidence"
            or row.get("worker") != worker["worker"]
            or row.get("source_commit") != source_commit
            or row.get("protocol_id") != protocol["protocol_id"]
            or row.get("predecessor_protocol_id") != U002_PROTOCOL_ID_V1
            or row.get("parent_training_closure") is not True
            or row.get("optimizer_smoke") is not True
            or row.get("filesystem_mutation") is not False
        ):
            raise LearnedResourceForecastEvidenceSuccessorLauncherV1Error(
                "U004 global preflight returned foreign summary"
            )
        preflight_rows.append(row)
    dispatch = dispatcher or _ssh_dispatch
    dispatched = []
    with _DispatchStatusV1(dispatch_path) as status:
        status.emit(
            {
                "event": "GLOBAL_PRECHECK_COMPLETED",
                "phase": "evidence",
                "prechecked_worker_count": 6,
                "optimizer_smoke_all_passed": True,
                "parent_training_closure_all_passed": True,
                "model_evaluation_authority_is_read_only_u002": True,
                "model_evaluation_reexecuted_in_u004": False,
                "filesystem_mutation_before_precheck_completed": False,
            }
        )
        status.emit(
            {
                "event": "DISPATCH_STARTED",
                "phase": "evidence",
                "source_commit": source_commit,
                "protocol_id": protocol["protocol_id"],
                "predecessor_protocol_id": U002_PROTOCOL_ID_V1,
                "model_evaluation_authority_is_read_only_u002": True,
                "model_evaluation_reexecuted_in_u004": False,
                "worker_count": 6,
                "u002_failed_evidence_dispatch_eligible": False,
            }
        )
        seen_hosts: set[str] = set()
        for worker in workers:
            command, worker_root, worker_status, worker_log = _remote_worker_command(
                worker=worker,
                protocol_path=protocol_path,
                manifest_path=manifest_path,
                source_checkout=source_checkout,
                source_pythonpath=source_pythonpath,
                results_root=results_root,
                status_root=status_root,
                log_root=log_root,
                first_worker_for_host=worker["host_alias"] not in seen_hosts,
            )
            seen_hosts.add(worker["host_alias"])
            try:
                pid = dispatch(worker["host_alias"], command)
            except Exception as error:
                status.emit(
                    {
                        "event": "WORKER_DISPATCH_FAILED",
                        "phase": "evidence",
                        "worker": worker["worker"],
                        "host_alias": worker["host_alias"],
                        "failure_kind": type(error).__name__,
                        "failure_message": str(error),
                    }
                )
                status.emit(
                    {
                        "event": "DISPATCH_FAILED",
                        "phase": "evidence",
                        "dispatched_worker_count": len(dispatched),
                        "same_identity_retry_allowed": False,
                    }
                )
                raise
            row = {
                "worker": worker["worker"],
                "host_alias": worker["host_alias"],
                "expected_hostname": worker["expected_hostname"],
                "device": worker["device"],
                "remote_pid": int(pid),
                "predecessor_snapshot_root": worker["predecessor_snapshot_root"],
                "worker_results_root": str(worker_root),
                "worker_status_stream": str(worker_status),
                "worker_log": str(worker_log),
            }
            dispatched.append(row)
            status.emit({"event": "WORKER_DISPATCHED", "phase": "evidence", **row})
        status.emit(
            {
                "event": "DISPATCH_COMPLETED",
                "phase": "evidence",
                "dispatched_worker_count": 6,
                "worker_execution_completed": False,
            }
        )
    return {
        "success": True,
        "phase": "evidence",
        "source_commit": source_commit,
        "protocol_id": protocol["protocol_id"],
        "predecessor_protocol_id": U002_PROTOCOL_ID_V1,
        "dispatched_worker_count": 6,
        "workers": dispatched,
        "worker_execution_completed": False,
        "dispatch_status": str(dispatch_path),
        "same_identity_retry_allowed": False,
        "ssh_control_master_disabled": True,
    }


def main() -> int:
    try:
        summary = _launch(_arguments())
    except (
        LearnedResourceForecastEvidenceSuccessorLauncherV1Error,
        LearnedResourceForecastEvidenceSuccessorProtocolV1Error,
        ScienceExecutionIOV1Error,
        ValueError,
    ) as error:
        raise SystemExit(str(error)) from error
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
