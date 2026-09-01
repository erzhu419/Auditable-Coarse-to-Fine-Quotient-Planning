#!/usr/bin/env python3
"""Durably dispatch all six workers for one frozen U002 phase."""

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
from acfqp.science.learned_resource_forecast_protocol_v1 import (
    LearnedResourceForecastProtocolV1Error,
    validate_ratified_learned_resource_forecast_protocol_v1,
)


REPOSITORY = Path(__file__).resolve().parents[1]
WORKER_SCRIPT_NAME_V1 = "run_learned_resource_forecast_worker_u002.py"
PHASES_V1 = ("training", "evidence")
DispatcherV1 = Callable[[str, str], str]
GlobalPreflightV1 = Callable[[str, str], dict[str, Any]]


class LearnedResourceForecastLauncherV1Error(RuntimeError):
    """The launch binding, remote dispatch, or one-shot identity failed."""


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=PHASES_V1, required=True)
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
        raise LearnedResourceForecastLauncherV1Error(
            f"cannot read {label} as one JSON object: {path}"
        ) from error
    if type(value) is not dict:
        raise LearnedResourceForecastLauncherV1Error(
            f"{label} must contain one JSON object"
        )
    return value


def _load_prepare_module():
    path = REPOSITORY / "scripts/prepare_learned_resource_forecast_campaign_u002.py"
    spec = importlib.util.spec_from_file_location("acfqp_u002_prepare_for_launch", path)
    if spec is None or spec.loader is None:
        raise LearnedResourceForecastLauncherV1Error(
            "cannot load the U002 launch-manifest authority"
        )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_history_scan_module():
    path = REPOSITORY / "scripts/scan_learned_resource_forecast_history_u002.py"
    spec = importlib.util.spec_from_file_location("acfqp_u002_scan_for_launch", path)
    if spec is None or spec.loader is None:
        raise LearnedResourceForecastLauncherV1Error(
            "cannot load the U002 history-scan authority"
        )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_postprocess_module():
    path = REPOSITORY / "scripts/postprocess_retain_learned_resource_forecast_u002.py"
    spec = importlib.util.spec_from_file_location(
        "acfqp_u002_postprocess_for_launch", path
    )
    if spec is None or spec.loader is None:
        raise LearnedResourceForecastLauncherV1Error(
            "cannot load the U002 dispatch-status authority"
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
            raise LearnedResourceForecastLauncherV1Error(
                "dispatch status already exists; the launch identity is consumed"
            ) from error
        return self

    def emit(self, event: dict[str, Any]) -> None:
        if self._fd is None or type(event) is not dict:
            raise LearnedResourceForecastLauncherV1Error(
                "dispatch status is not open for one JSON event"
            )
        view = memoryview(canonical_json_bytes(event) + b"\n")
        while view:
            written = os.write(self._fd, view)
            view = view[written:]
        os.fsync(self._fd)

    def __exit__(self, _type, _value, _traceback) -> None:
        if self._fd is not None:
            os.close(self._fd)
            self._fd = None


def _remote_worker_command(
    *,
    phase: str,
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
    worker_index = worker["worker"]
    worker_results_root = results_root / f"worker-{worker_index}"
    status_name = worker[
        "policy_training_status_stream"
        if phase == "training"
        else "player_evidence_status_stream"
    ]
    status_path = status_root / status_name
    log_path = log_root / f"worker-{worker_index}-{phase}.log"
    worker_script = source_checkout / "scripts" / WORKER_SCRIPT_NAME_V1
    process_arguments = [
        "env",
        f"PYTHONPATH={source_pythonpath}",
        worker["python"],
        str(worker_script),
        "--worker",
        str(worker_index),
        "--phase",
        phase,
        "--protocol",
        str(protocol_path),
        "--manifest",
        str(manifest_path),
        "--results-root",
        str(worker_results_root),
        "--status-stream",
        str(status_path),
        "--device",
        worker["device"],
    ]
    preflight_arguments = [*process_arguments, "--preflight-only"]
    setup_arguments = [
        "set -eu",
        "umask 077",
        f"test -x {shlex.quote(worker['python'])}",
        f"test -f {shlex.quote(str(worker_script))}",
        f"test -d {shlex.quote(str(source_pythonpath))}",
        f"test -f {shlex.quote(str(protocol_path))}",
        f"test -f {shlex.quote(str(manifest_path))}",
        f"test ! -e {shlex.quote(str(status_path))}",
        f"test ! -e {shlex.quote(str(log_path))}",
    ]
    if phase == "training":
        if first_worker_for_host:
            setup_arguments.extend(
                [
                    f"test ! -e {shlex.quote(str(results_root))}",
                    f"test ! -e {shlex.quote(str(status_root))}",
                    f"test ! -e {shlex.quote(str(log_root))}",
                    f"mkdir {shlex.quote(str(results_root))} "
                    f"{shlex.quote(str(status_root))} {shlex.quote(str(log_root))}",
                ]
            )
        else:
            setup_arguments.extend(
                [
                    f"test -d {shlex.quote(str(results_root))}",
                    f"test -d {shlex.quote(str(status_root))}",
                    f"test -d {shlex.quote(str(log_root))}",
                ]
            )
        setup_arguments.extend(
            [
                f"test ! -e {shlex.quote(str(worker_results_root))}",
                f"mkdir {shlex.quote(str(worker_results_root))}",
            ]
        )
    else:
        setup_arguments.extend(
            [
                f"test -d {shlex.quote(str(results_root))}",
                f"test -d {shlex.quote(str(status_root))}",
                f"test -d {shlex.quote(str(log_root))}",
                f"test -d {shlex.quote(str(worker_results_root))}",
            ]
        )
    launch = (
        f"{shlex.join(preflight_arguments)} > /dev/null; "
        f"nohup {shlex.join(process_arguments)} "
        f"> {shlex.quote(str(log_path))} 2>&1 < /dev/null & "
        'worker_pid=$!; printf "%s\\n" "$worker_pid"'
    )
    return (
        "; ".join((*setup_arguments, launch)),
        worker_results_root,
        status_path,
        log_path,
    )


def _remote_global_preflight_command(
    *,
    phase: str,
    worker: dict[str, Any],
    protocol_path: Path,
    manifest_path: Path,
    source_checkout: Path,
    source_pythonpath: Path,
    results_root: Path,
    status_root: Path,
    log_root: Path,
) -> str:
    worker_index = worker["worker"]
    status_name = worker[
        "policy_training_status_stream"
        if phase == "training"
        else "player_evidence_status_stream"
    ]
    status_path = status_root / status_name
    log_path = log_root / f"worker-{worker_index}-{phase}.log"
    worker_script = source_checkout / "scripts" / WORKER_SCRIPT_NAME_V1
    process_arguments = [
        "env",
        f"PYTHONPATH={source_pythonpath}",
        worker["python"],
        str(worker_script),
        "--worker",
        str(worker_index),
        "--phase",
        phase,
        "--protocol",
        str(protocol_path),
        "--manifest",
        str(manifest_path),
        "--results-root",
        str(results_root / f"worker-{worker_index}"),
        "--status-stream",
        str(status_path),
        "--device",
        worker["device"],
        "--global-preflight-only",
    ]
    checks = [
        "set -eu",
        f"test -x {shlex.quote(worker['python'])}",
        f"test -f {shlex.quote(str(worker_script))}",
        f"test -d {shlex.quote(str(source_pythonpath))}",
        f"test -f {shlex.quote(str(protocol_path))}",
        f"test -f {shlex.quote(str(manifest_path))}",
        f"test ! -e {shlex.quote(str(status_path))}",
        f"test ! -e {shlex.quote(str(log_path))}",
        shlex.join(process_arguments),
    ]
    command = "; ".join(checks)
    if "mkdir" in command or "nohup" in command or ">" in command:
        raise AssertionError("global preflight stopped being read-only")
    return command


def _ssh_dispatch(host_alias: str, remote_command: str) -> str:
    completed = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", host_alias, remote_command],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise LearnedResourceForecastLauncherV1Error(
            f"remote dispatch failed on {host_alias}: {completed.stderr.strip()}"
        )
    pid = completed.stdout.strip()
    if not pid.isdecimal() or int(pid) <= 0:
        raise LearnedResourceForecastLauncherV1Error(
            f"remote dispatch on {host_alias} returned no exact worker PID"
        )
    return pid


def _ssh_global_preflight(host_alias: str, remote_command: str) -> dict[str, Any]:
    completed = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", host_alias, remote_command],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise LearnedResourceForecastLauncherV1Error(
            f"global preflight failed on {host_alias}: {completed.stderr.strip()}"
        )
    try:
        value = json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        raise LearnedResourceForecastLauncherV1Error(
            f"global preflight on {host_alias} returned no exact JSON summary"
        ) from error
    if type(value) is not dict:
        raise LearnedResourceForecastLauncherV1Error(
            "global preflight returned a non-object summary"
        )
    return value


def _outside(path: Path, label: str) -> Path:
    resolved = require_path_outside_repository_v1(
        repository=REPOSITORY, path=path, label=label
    )
    if not resolved.is_absolute():  # pragma: no cover - resolve is absolute
        raise AssertionError("outside-path resolver stopped returning absolutes")
    return resolved


def _launch(
    args: argparse.Namespace,
    *,
    dispatcher: DispatcherV1 | None = None,
    global_preflight: GlobalPreflightV1 | None = None,
) -> dict[str, Any]:
    if args.phase not in PHASES_V1:
        raise LearnedResourceForecastLauncherV1Error(
            "launch phase is outside the frozen U002 roster"
        )
    protocol_path = _outside(args.protocol, "ratified U002 protocol input")
    manifest_path = _outside(args.manifest, "U002 launch manifest input")
    history_receipt_path = _outside(
        args.history_scan_receipt, "U002 history-scan receipt"
    )
    results_root = _outside(args.remote_results_root, "remote U002 results root")
    status_root = _outside(args.remote_status_root, "remote U002 status root")
    log_root = _outside(args.remote_log_root, "remote U002 log root")
    dispatch_path = _outside(args.dispatch_status, "U002 dispatch status")
    source_commit = bound_clean_source_commit_v1(REPOSITORY)
    protocol = validate_ratified_learned_resource_forecast_protocol_v1(
        _read_object(protocol_path, "ratified U002 protocol")
    )
    manifest = _read_object(manifest_path, "U002 launch manifest")
    prepare = _load_prepare_module()
    if manifest != prepare.build_launch_manifest_v1(protocol):
        raise LearnedResourceForecastLauncherV1Error(
            "launch manifest does not replay from the ratified protocol"
        )
    source_checkout = Path(manifest["source_checkout"]).resolve()
    source_pythonpath = Path(manifest["source_pythonpath"]).resolve()
    fixed = manifest["fixed_paths"]
    expected_dispatch_path = Path(
        fixed[
            "training_dispatch_status"
            if args.phase == "training"
            else "evidence_dispatch_status"
        ]
    ).resolve()
    if (
        source_commit != protocol["source_commit"]
        or source_commit != manifest["source_commit"]
        or source_checkout != REPOSITORY.resolve()
        or source_pythonpath != source_checkout / "src"
        or manifest["required_runtime"]["source_pythonpath"]
        != str(source_pythonpath)
        or manifest["worker_count"] != 6
        or len(manifest["workers"]) != 6
        or protocol_path != Path(fixed["protocol"]).resolve()
        or manifest_path != Path(fixed["manifest"]).resolve()
        or history_receipt_path
        != Path(fixed["history_scan_receipt"]).resolve()
        or results_root != Path(fixed["results_root"]).resolve()
        or status_root != Path(fixed["status_root"]).resolve()
        or log_root != Path(fixed["log_root"]).resolve()
        or dispatch_path != expected_dispatch_path
    ):
        raise LearnedResourceForecastLauncherV1Error(
            "launch source, protocol, manifest, or source PYTHONPATH binding changed"
        )
    scan = _load_history_scan_module()
    scan.validate_history_scan_receipt_v1(
        _read_object(history_receipt_path, "U002 history-scan receipt"),
        protocol,
        manifest,
    )
    if args.phase == "evidence":
        postprocess = _load_postprocess_module()
        postprocess._validate_dispatch_status(
            Path(fixed["training_dispatch_status"]),
            phase="training",
            manifest=manifest,
            fixed=fixed,
        )
    if dispatch_path.exists():
        raise LearnedResourceForecastLauncherV1Error(
            "dispatch status already exists; the launch identity is consumed"
        )

    dispatch = dispatcher or _ssh_dispatch
    preflight = global_preflight or _ssh_global_preflight
    preflight_rows: list[dict[str, Any]] = []
    for worker in manifest["workers"]:
        command = _remote_global_preflight_command(
            phase=args.phase,
            worker=worker,
            protocol_path=protocol_path,
            manifest_path=manifest_path,
            source_checkout=source_checkout,
            source_pythonpath=source_pythonpath,
            results_root=results_root,
            status_root=status_root,
            log_root=log_root,
        )
        row = preflight(worker["host_alias"], command)
        if (
            row.get("success") is not True
            or row.get("global_preflight_only") is not True
            or row.get("optimizer_smoke") is not True
            or row.get("filesystem_mutation") is not False
            or row.get("phase") != args.phase
            or row.get("worker") != worker["worker"]
            or row.get("source_commit") != source_commit
            or row.get("protocol_id") != protocol["protocol_id"]
        ):
            raise LearnedResourceForecastLauncherV1Error(
                "global preflight returned a foreign worker summary"
            )
        preflight_rows.append(row)
    dispatched: list[dict[str, Any]] = []
    with _DispatchStatusV1(dispatch_path) as status:
        status.emit(
            {
                "event": "GLOBAL_PRECHECK_COMPLETED",
                "phase": args.phase,
                "prechecked_worker_count": len(preflight_rows),
                "optimizer_smoke_worker_count": sum(
                    row["optimizer_smoke"] is True for row in preflight_rows
                ),
                "optimizer_smoke_all_passed": True,
                "filesystem_mutation_before_precheck_completed": False,
            }
        )
        status.emit(
            {
                "event": "DISPATCH_STARTED",
                "phase": args.phase,
                "source_commit": source_commit,
                "protocol_id": protocol["protocol_id"],
                "source_checkout": str(source_checkout),
                "source_pythonpath": str(source_pythonpath),
                "worker_count": 6,
            }
        )
        seen_hosts: set[str] = set()
        for worker in manifest["workers"]:
            (
                command,
                worker_results,
                worker_status,
                worker_log,
            ) = _remote_worker_command(
                phase=args.phase,
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
                        "phase": args.phase,
                        "worker": worker["worker"],
                        "host_alias": worker["host_alias"],
                        "failure_kind": type(error).__name__,
                        "failure_message": str(error),
                    }
                )
                status.emit(
                    {
                        "event": "DISPATCH_FAILED",
                        "phase": args.phase,
                        "dispatched_worker_count": len(dispatched),
                    }
                )
                raise
            row = {
                "worker": worker["worker"],
                "host_alias": worker["host_alias"],
                "expected_hostname": worker["expected_hostname"],
                "device": worker["device"],
                "remote_pid": int(pid),
                "worker_results_root": str(worker_results),
                "worker_status_stream": str(worker_status),
                "worker_log": str(worker_log),
            }
            dispatched.append(row)
            status.emit(
                {"event": "WORKER_DISPATCHED", "phase": args.phase, **row}
            )
        status.emit(
            {
                "event": "DISPATCH_COMPLETED",
                "phase": args.phase,
                "dispatched_worker_count": len(dispatched),
                "worker_execution_completed": False,
            }
        )
    return {
        "success": True,
        "phase": args.phase,
        "source_commit": source_commit,
        "protocol_id": protocol["protocol_id"],
        "source_pythonpath": str(source_pythonpath),
        "dispatched_worker_count": len(dispatched),
        "workers": dispatched,
        "worker_execution_completed": False,
        "dispatch_status": str(dispatch_path),
    }


def main() -> int:
    try:
        summary = _launch(_arguments())
    except (
        LearnedResourceForecastLauncherV1Error,
        LearnedResourceForecastProtocolV1Error,
        ScienceExecutionIOV1Error,
    ) as error:
        raise SystemExit(str(error)) from error
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
