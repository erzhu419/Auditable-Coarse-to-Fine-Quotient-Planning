#!/usr/bin/env python3
"""Gather remote U002 evidence to gpu2 by a retryable server-side tar stream."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
from pathlib import Path
import shlex
import socket
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
from acfqp.science.learned_resource_forecast_protocol_v1 import (
    LearnedResourceForecastProtocolV1Error,
    validate_ratified_learned_resource_forecast_protocol_v1,
)


REPOSITORY = Path(__file__).resolve().parents[1]
SCHEMA_V1 = "acfqp.science.learned_resource_forecast_gather_receipt.v1"
MARKER_SCHEMA_V1 = "acfqp.science.learned_resource_forecast_gather_marker.v1"
REMOTE_WORKERS_V1 = (2, 3, 4, 5)
SourceInspectorV1 = Callable[[str, dict[str, Any]], dict[str, Any]]
TransporterV1 = Callable[[str, dict[str, Any]], None]
CentralInspectorV1 = Callable[[str, dict[str, Any]], dict[str, Any]]
SmallFileCopierV1 = Callable[[str, Path, bytes, str], None]


class LearnedResourceForecastGatherV1Error(RuntimeError):
    """Remote evidence ownership, transport, or gather receipt is not exact."""


def _load_script_module(name: str, filename: str):
    path = REPOSITORY / "scripts" / filename
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise LearnedResourceForecastGatherV1Error(
            f"cannot load registered gather dependency: {path}"
        )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_prepare_module():
    return _load_script_module(
        "acfqp_u002_prepare_for_gather",
        "prepare_learned_resource_forecast_campaign_u002.py",
    )


def _load_history_scan_module():
    return _load_script_module(
        "acfqp_u002_history_for_gather",
        "scan_learned_resource_forecast_history_u002.py",
    )


def _load_postprocess_module():
    return _load_script_module(
        "acfqp_u002_postprocess_for_gather",
        "postprocess_retain_learned_resource_forecast_u002.py",
    )


def _read_object(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise LearnedResourceForecastGatherV1Error(
            f"cannot read {label} as one JSON object: {path}"
        ) from error
    if type(value) is not dict:
        raise LearnedResourceForecastGatherV1Error(
            f"{label} must contain one JSON object"
        )
    return value


def _common_root(manifest: dict[str, Any]) -> Path:
    fixed = manifest["fixed_paths"]
    parents = {
        Path(fixed[key]).resolve().parent
        for key in ("results_root", "status_root", "log_root")
    }
    if len(parents) != 1:
        raise LearnedResourceForecastGatherV1Error(
            "gather roots no longer share one server-side parent"
        )
    return parents.pop()


def _worker_file_paths(
    manifest: dict[str, Any], worker_index: int
) -> list[Path]:
    fixed = manifest["fixed_paths"]
    worker = manifest["workers"][worker_index]
    root = Path(fixed["results_root"]) / f"worker-{worker_index}"
    names: list[str] = []
    for job in worker["policy_training_jobs"]:
        names.append(job["result_filename"])
        names.extend(job["checkpoint_filenames"])
    for job in worker["player_evidence_jobs"]:
        names.extend((job["label_filename"], job["probe_filename"]))
        if job["split"] == "TRAIN":
            names.extend(
                (
                    job["trajectory_metadata_filename"],
                    job["trajectory_array_filename"],
                )
            )
    paths = [root / name for name in names]
    paths.extend(
        Path(fixed["status_root"]) / worker[key]
        for key in (
            "policy_training_status_stream",
            "player_evidence_status_stream",
        )
    )
    paths.extend(
        Path(fixed["log_root"]) / f"worker-{worker_index}-{phase}.log"
        for phase in ("training", "evidence")
    )
    if len(paths) not in (334, 352) or len(set(paths)) != len(paths):
        raise LearnedResourceForecastGatherV1Error(
            "remote worker gather file roster changed"
        )
    return paths


def _host_workers(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for host_alias in ("jtl110gpu", "jtl311linux"):
        workers = [
            worker["worker"]
            for worker in manifest["workers"]
            if worker["host_alias"] == host_alias
        ]
        if len(workers) != 2 or any(index not in REMOTE_WORKERS_V1 for index in workers):
            raise LearnedResourceForecastGatherV1Error(
                "remote gather host ownership differs from the manifest"
            )
        first = manifest["workers"][workers[0]]
        rows.append(
            {
                "host_alias": host_alias,
                "expected_hostname": first["expected_hostname"],
                "python": first["python"],
                "workers": workers,
            }
        )
    return rows


def _inspect_local_source(
    protocol: dict[str, Any], manifest: dict[str, Any], worker_indices: list[int]
) -> dict[str, Any]:
    if bound_clean_source_commit_v1(REPOSITORY) != protocol["source_commit"]:
        raise LearnedResourceForecastGatherV1Error(
            "remote gather source commit differs from the protocol"
        )
    postprocess = _load_postprocess_module()
    fixed = manifest["fixed_paths"]
    expected_hostname = manifest["workers"][worker_indices[0]]["expected_hostname"]
    if socket.gethostname() != expected_hostname:
        raise LearnedResourceForecastGatherV1Error(
            "remote gather source hostname differs from manifest ownership"
        )
    for index in worker_indices:
        worker = manifest["workers"][index]
        if worker["expected_hostname"] != expected_hostname:
            raise LearnedResourceForecastGatherV1Error(
                "remote workers do not share their registered source host"
            )
        worker_root = Path(fixed["results_root"]) / f"worker-{index}"
        artifacts = postprocess._worker_artifact_map(worker)
        postprocess._require_exact_directory(
            worker_root, set(artifacts), f"remote worker-{index} result directory"
        )
        for phase, status_key in (
            ("training", "policy_training_status_stream"),
            ("evidence", "player_evidence_status_stream"),
        ):
            postprocess._validate_worker_status(
                Path(fixed["status_root"]) / worker[status_key],
                phase=phase,
                worker=worker,
            )
            postprocess._validate_worker_log(
                Path(fixed["log_root"]) / f"worker-{index}-{phase}.log",
                phase=phase,
                worker=worker,
                results_root=worker_root,
            )
    common = _common_root(manifest)
    files = []
    for index in worker_indices:
        for path in _worker_file_paths(manifest, index):
            if not path.is_file():
                raise LearnedResourceForecastGatherV1Error(
                    f"remote gather source file disappeared: {path}"
                )
            files.append(
                {
                    "relative_path": path.resolve().relative_to(common).as_posix(),
                    "size_bytes": path.stat().st_size,
                }
            )
    return {
        "actual_hostname": socket.gethostname(),
        "workers": worker_indices,
        "files": files,
        "job_reexecution": False,
    }


def _ssh_source_inspector(host_alias: str, request: dict[str, Any]) -> dict[str, Any]:
    script = REPOSITORY / "scripts/gather_learned_resource_forecast_evidence_u002.py"
    command = [
        "env",
        f"PYTHONPATH={request['source_pythonpath']}",
        request["python"],
        str(script),
        "--source-inspect-only",
        "--protocol",
        request["protocol"],
        "--manifest",
        request["manifest"],
        "--workers",
        ",".join(str(value) for value in request["workers"]),
    ]
    completed = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", host_alias, shlex.join(command)],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise LearnedResourceForecastGatherV1Error(
            f"remote gather inspection failed on {host_alias}: {completed.stderr.strip()}"
        )
    try:
        result = json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        raise LearnedResourceForecastGatherV1Error(
            f"remote gather inspection on {host_alias} returned no exact JSON"
        ) from error
    if type(result) is not dict:
        raise LearnedResourceForecastGatherV1Error(
            "remote gather inspection returned a non-object"
        )
    return result


def _tar_stream_transport(host_alias: str, request: dict[str, Any]) -> None:
    members = request["tar_members"]
    common_root = request["common_root"]
    remote = subprocess.Popen(
        [
            "ssh",
            "-o",
            "BatchMode=yes",
            host_alias,
            "tar",
            "-C",
            common_root,
            "-cf",
            "-",
            "--",
            *members,
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert remote.stdout is not None
    local = subprocess.run(
        [
            "ssh",
            "-o",
            "BatchMode=yes",
            request["central_host_alias"],
            "tar",
            "-C",
            common_root,
            "-xf",
            "-",
        ],
        stdin=remote.stdout,
        check=False,
        capture_output=True,
    )
    remote.stdout.close()
    assert remote.stderr is not None
    remote_stderr = remote.stderr.read()
    remote_returncode = remote.wait()
    if remote_returncode != 0 or local.returncode != 0:
        raise LearnedResourceForecastGatherV1Error(
            "server-to-server tar stream failed: "
            + remote_stderr.decode(errors="replace").strip()
            + " "
            + local.stderr.decode(errors="replace").strip()
        )


def _copy_small_to_remote(
    host_alias: str, path: Path, raw: bytes, python_path: str
) -> None:
    program = """import os
import pathlib
import sys
p = pathlib.Path(sys.argv[1])
d = sys.stdin.buffer.read()
p.parent.mkdir(parents=True, exist_ok=True)
if p.is_file() and p.read_bytes() == d:
    raise SystemExit(0)
if p.exists():
    raise SystemExit(3)
fd = os.open(p, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
with os.fdopen(fd, "wb") as stream:
    stream.write(d)
    stream.flush()
    os.fsync(stream.fileno())
"""
    remote_command = shlex.join([python_path, "-c", program, str(path)])
    completed = subprocess.run(
        [
            "ssh",
            "-o",
            "BatchMode=yes",
            host_alias,
            remote_command,
        ],
        input=raw,
        check=False,
        capture_output=True,
    )
    if completed.returncode != 0:
        raise LearnedResourceForecastGatherV1Error(
            f"small authority copy failed for {path}: "
            + completed.stderr.decode(errors="replace").strip()
        )


def _inspect_central_local(
    protocol: dict[str, Any], manifest: dict[str, Any], state: str
) -> dict[str, Any]:
    if state not in {"FIRST", "RETRY", "COMPLETE"}:
        raise LearnedResourceForecastGatherV1Error("unknown central gather state")
    if (
        bound_clean_source_commit_v1(REPOSITORY) != protocol["source_commit"]
        or socket.gethostname()
        != manifest["central_analysis"]["expected_hostname"]
    ):
        raise LearnedResourceForecastGatherV1Error(
            "central gather inspection source or hostname changed"
        )
    postprocess = _load_postprocess_module()
    fixed = manifest["fixed_paths"]
    results_root = Path(fixed["results_root"])
    status_root = Path(fixed["status_root"])
    log_root = Path(fixed["log_root"])
    if not all(path.is_dir() for path in (results_root, status_root, log_root)):
        raise LearnedResourceForecastGatherV1Error(
            "central gather roots are not existing directories"
        )
    local_indices = (0, 1)
    allowed_indices = local_indices if state == "FIRST" else tuple(range(6))
    result_entries = list(results_root.iterdir())
    if (
        any(not path.is_dir() for path in result_entries)
        or not {path.name for path in result_entries}.issubset(
            {f"worker-{index}" for index in allowed_indices}
        )
        or not {f"worker-{index}" for index in local_indices}.issubset(
            {path.name for path in result_entries}
        )
        or (
            state in {"FIRST", "COMPLETE"}
            and {path.name for path in result_entries}
            != {f"worker-{index}" for index in allowed_indices}
        )
    ):
        raise LearnedResourceForecastGatherV1Error(
            "central results root differs from the gather state"
        )
    all_status_names = {
        worker[key]
        for worker in manifest["workers"]
        for key in (
            "policy_training_status_stream",
            "player_evidence_status_stream",
        )
    }
    local_status_names = {
        manifest["workers"][index][key]
        for index in local_indices
        for key in (
            "policy_training_status_stream",
            "player_evidence_status_stream",
        )
    }
    all_log_names = {
        f"worker-{index}-{phase}.log"
        for index in range(6)
        for phase in ("training", "evidence")
    }
    local_log_names = {
        f"worker-{index}-{phase}.log"
        for index in local_indices
        for phase in ("training", "evidence")
    }
    actual_status = {path.name for path in status_root.iterdir() if path.is_file()}
    actual_logs = {path.name for path in log_root.iterdir() if path.is_file()}
    if (
        len(actual_status) != len(list(status_root.iterdir()))
        or len(actual_logs) != len(list(log_root.iterdir()))
        or not local_status_names.issubset(actual_status)
        or not local_log_names.issubset(actual_logs)
        or not actual_status.issubset(all_status_names)
        or not actual_logs.issubset(all_log_names)
        or (state == "FIRST" and actual_status != local_status_names)
        or (state == "FIRST" and actual_logs != local_log_names)
        or (state == "COMPLETE" and actual_status != all_status_names)
        or (state == "COMPLETE" and actual_logs != all_log_names)
    ):
        raise LearnedResourceForecastGatherV1Error(
            "central status or log root differs from the gather state"
        )
    indices_to_validate = local_indices if state != "COMPLETE" else tuple(range(6))
    for index in indices_to_validate:
        worker = manifest["workers"][index]
        worker_root = results_root / f"worker-{index}"
        postprocess._require_exact_directory(
            worker_root,
            set(postprocess._worker_artifact_map(worker)),
            f"central worker-{index} result directory",
        )
        for phase, status_key in (
            ("training", "policy_training_status_stream"),
            ("evidence", "player_evidence_status_stream"),
        ):
            postprocess._validate_worker_status(
                status_root / worker[status_key], phase=phase, worker=worker
            )
            postprocess._validate_worker_log(
                log_root / f"worker-{index}-{phase}.log",
                phase=phase,
                worker=worker,
                results_root=worker_root,
            )
    for phase, key in (
        ("training", "training_dispatch_status"),
        ("evidence", "evidence_dispatch_status"),
    ):
        postprocess._validate_dispatch_status(
            Path(fixed[key]), phase=phase, manifest=manifest, fixed=fixed
        )
    common = _common_root(manifest)
    files = []
    for index in REMOTE_WORKERS_V1:
        for path in _worker_file_paths(manifest, index):
            if path.is_file():
                files.append(
                    {
                        "relative_path": path.resolve().relative_to(common).as_posix(),
                        "size_bytes": path.stat().st_size,
                    }
                )
    return {
        "actual_hostname": socket.gethostname(),
        "state": state,
        "files": files,
        "job_reexecution": False,
    }


def _ssh_central_inspector(host_alias: str, request: dict[str, Any]) -> dict[str, Any]:
    script = REPOSITORY / "scripts/gather_learned_resource_forecast_evidence_u002.py"
    command = [
        "env",
        f"PYTHONPATH={request['source_pythonpath']}",
        request["python"],
        str(script),
        "--central-inspect-only",
        "--central-state",
        request["state"],
        "--protocol",
        request["protocol"],
        "--manifest",
        request["manifest"],
    ]
    completed = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", host_alias, shlex.join(command)],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise LearnedResourceForecastGatherV1Error(
            "central gather inspection failed: " + completed.stderr.strip()
        )
    try:
        value = json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        raise LearnedResourceForecastGatherV1Error(
            "central gather inspection returned no exact JSON"
        ) from error
    if type(value) is not dict:
        raise LearnedResourceForecastGatherV1Error(
            "central gather inspection returned a non-object"
        )
    return value


def _marker(protocol: dict[str, Any], manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": MARKER_SCHEMA_V1,
        "protocol_id": protocol["protocol_id"],
        "source_commit": protocol["source_commit"],
        "central_host_alias": manifest["central_analysis"]["host_alias"],
        "central_expected_hostname": manifest["central_analysis"][
            "expected_hostname"
        ],
        "remote_workers": list(REMOTE_WORKERS_V1),
        "transport_is_evidence_fetch_not_job_execution": True,
        "transport_retry_may_only_overwrite_registered_destination_files": True,
    }


def _validate_inspection(
    row: dict[str, Any], expected: dict[str, Any], manifest: dict[str, Any]
) -> list[dict[str, Any]]:
    common = _common_root(manifest)
    expected_paths = {
        path.resolve().relative_to(common).as_posix()
        for index in expected["workers"]
        for path in _worker_file_paths(manifest, index)
    }
    files = row.get("files")
    if (
        row.get("actual_hostname") != expected["expected_hostname"]
        or row.get("workers") != expected["workers"]
        or row.get("job_reexecution") is not False
        or type(files) is not list
        or {file.get("relative_path") for file in files} != expected_paths
        or any(
            type(file.get("size_bytes")) is not int or file["size_bytes"] < 0
            for file in files
        )
    ):
        raise LearnedResourceForecastGatherV1Error(
            "remote source inspection differs from exact manifest ownership"
        )
    return files


def _validate_central_files(
    inspections: list[dict[str, Any]], manifest: dict[str, Any]
) -> None:
    common = _common_root(manifest)
    for inspection in inspections:
        for file in inspection["files"]:
            path = common / file["relative_path"]
            if not path.is_file() or path.stat().st_size != file["size_bytes"]:
                raise LearnedResourceForecastGatherV1Error(
                    "gathered central file is missing or size-incomplete"
                )
    postprocess = _load_postprocess_module()
    fixed = manifest["fixed_paths"]
    for index in REMOTE_WORKERS_V1:
        worker = manifest["workers"][index]
        worker_root = Path(fixed["results_root"]) / f"worker-{index}"
        postprocess._require_exact_directory(
            worker_root,
            set(postprocess._worker_artifact_map(worker)),
            f"gathered worker-{index} result directory",
        )


def _validate_central_inspection(
    row: dict[str, Any],
    *,
    state: str,
    manifest: dict[str, Any],
    expected_files: list[dict[str, Any]] | None = None,
) -> None:
    files = row.get("files")
    if (
        row.get("actual_hostname")
        != manifest["central_analysis"]["expected_hostname"]
        or row.get("state") != state
        or row.get("job_reexecution") is not False
        or type(files) is not list
        or len({file.get("relative_path") for file in files}) != len(files)
        or any(
            type(file.get("relative_path")) is not str
            or type(file.get("size_bytes")) is not int
            or file["size_bytes"] < 0
            for file in files
        )
    ):
        raise LearnedResourceForecastGatherV1Error(
            "central inspector returned a foreign gather state"
        )
    if state == "FIRST" and files:
        raise LearnedResourceForecastGatherV1Error(
            "central first gather state already contains remote evidence"
        )
    if expected_files is not None and {
        (file["relative_path"], file["size_bytes"]) for file in files
    } != {
        (file["relative_path"], file["size_bytes"]) for file in expected_files
    }:
        raise LearnedResourceForecastGatherV1Error(
            "central gathered files differ from source inspection sizes"
        )


def _validate_receipt_structure(
    receipt: dict[str, Any], protocol: dict[str, Any], manifest: dict[str, Any]
) -> list[dict[str, Any]]:
    hosts = receipt.get("source_hosts")
    if (
        receipt.get("schema") != SCHEMA_V1
        or receipt.get("protocol_id") != protocol["protocol_id"]
        or receipt.get("source_commit") != protocol["source_commit"]
        or receipt.get("central_expected_hostname")
        != manifest["central_analysis"]["expected_hostname"]
        or receipt.get("remote_workers") != list(REMOTE_WORKERS_V1)
        or receipt.get("transport_method")
        != "LOCAL_CONTROLLER_SSH_SOURCE_TAR_STDOUT_TO_SSH_GPU2_TAR_STDIN"
        or receipt.get("job_reexecution") is not False
        or type(hosts) is not list
        or len(hosts) != 2
    ):
        raise LearnedResourceForecastGatherV1Error(
            "gather receipt differs from its fixed evidence-fetch contract"
        )
    normalized = []
    for row, expected in zip(hosts, _host_workers(manifest), strict=True):
        files = _validate_inspection(row, expected, manifest)
        normalized.append({**row, "files": files})
    return normalized


def validate_gather_receipt_v1(
    receipt: dict[str, Any], protocol: dict[str, Any], manifest: dict[str, Any]
) -> dict[str, Any]:
    fixed = manifest["fixed_paths"]
    marker = _read_object(Path(fixed["gather_transport_marker"]), "gather marker")
    if marker != _marker(protocol, manifest):
        raise LearnedResourceForecastGatherV1Error(
            "gather marker differs from the fixed transport identity"
        )
    normalized = _validate_receipt_structure(receipt, protocol, manifest)
    _validate_central_files(normalized, manifest)
    return receipt


def _gather(
    *,
    protocol_path: Path,
    manifest_path: Path,
    history_path: Path,
    inspector: SourceInspectorV1 | None = None,
    transporter: TransporterV1 | None = None,
    central_inspector: CentralInspectorV1 | None = None,
    small_file_copier: SmallFileCopierV1 | None = None,
) -> dict[str, Any]:
    protocol = validate_ratified_learned_resource_forecast_protocol_v1(
        _read_object(protocol_path, "ratified U002 protocol")
    )
    manifest = _read_object(manifest_path, "U002 launch manifest")
    prepare = _load_prepare_module()
    if manifest != prepare.build_launch_manifest_v1(protocol):
        raise LearnedResourceForecastGatherV1Error(
            "launch manifest does not replay from the ratified protocol"
        )
    fixed = manifest["fixed_paths"]
    source_commit = bound_clean_source_commit_v1(REPOSITORY)
    if (
        source_commit != protocol["source_commit"]
        or REPOSITORY.resolve() != Path(fixed["source_checkout"]).resolve()
        or protocol_path.resolve() != Path(fixed["protocol"]).resolve()
        or manifest_path.resolve() != Path(fixed["manifest"]).resolve()
        or history_path.resolve() != Path(fixed["history_scan_receipt"]).resolve()
    ):
        raise LearnedResourceForecastGatherV1Error(
            "gather controller source or inputs differ from the manifest"
        )
    history = _load_history_scan_module()
    history.validate_history_scan_receipt_v1(
        _read_object(history_path, "history-scan receipt"), protocol, manifest
    )
    central_alias = manifest["central_analysis"]["host_alias"]
    central_python = manifest["workers"][0]["python"]
    inspect_central = central_inspector or _ssh_central_inspector
    copy_small = small_file_copier or _copy_small_to_remote
    for key in (
        "history_scan_receipt",
        "training_dispatch_status",
        "evidence_dispatch_status",
    ):
        authority_path = Path(fixed[key])
        if not authority_path.is_file():
            raise LearnedResourceForecastGatherV1Error(
                f"small gather authority is missing: {authority_path}"
            )
        copy_small(
            central_alias,
            authority_path,
            authority_path.read_bytes(),
            central_python,
        )

    receipt_path = Path(fixed["gather_receipt"])
    marker_path = Path(fixed["gather_transport_marker"])
    expected_marker = _marker(protocol, manifest)
    first_attempt = not marker_path.exists()
    if not first_attempt and _read_object(marker_path, "gather marker") != expected_marker:
        raise LearnedResourceForecastGatherV1Error(
            "existing gather marker differs from this transport identity"
        )
    if not first_attempt:
        copy_small(
            central_alias,
            marker_path,
            marker_path.read_bytes(),
            central_python,
        )

    inspect = inspector or _ssh_source_inspector
    transfer = transporter or _tar_stream_transport
    inspections: list[dict[str, Any]] = []
    common = _common_root(manifest)
    for expected in _host_workers(manifest):
        request = {
            "protocol": str(protocol_path),
            "manifest": str(manifest_path),
            "source_pythonpath": manifest["source_pythonpath"],
            "python": expected["python"],
            "workers": expected["workers"],
        }
        row = inspect(expected["host_alias"], request)
        files = _validate_inspection(row, expected, manifest)
        inspections.append(
            {
                "host_alias": expected["host_alias"],
                "expected_hostname": expected["expected_hostname"],
                **row,
                "files": files,
            }
        )
    expected_files = [
        file for inspection in inspections for file in inspection["files"]
    ]
    central_request = {
        "protocol": str(protocol_path),
        "manifest": str(manifest_path),
        "source_pythonpath": manifest["source_pythonpath"],
        "python": central_python,
    }
    if receipt_path.exists():
        if first_attempt:
            raise LearnedResourceForecastGatherV1Error(
                "gather receipt exists without its transport marker"
            )
        receipt = _read_object(receipt_path, "gather receipt")
        receipt_inspections = _validate_receipt_structure(
            receipt, protocol, manifest
        )
        if receipt_inspections != inspections:
            raise LearnedResourceForecastGatherV1Error(
                "existing gather receipt differs from fresh source inspection"
            )
        row = inspect_central(
            central_alias, {**central_request, "state": "COMPLETE"}
        )
        _validate_central_inspection(
            row,
            state="COMPLETE",
            manifest=manifest,
            expected_files=expected_files,
        )
        copy_small(
            central_alias,
            receipt_path,
            receipt_path.read_bytes(),
            central_python,
        )
        return receipt

    initial_state = "FIRST" if first_attempt else "RETRY"
    central_before = inspect_central(
        central_alias, {**central_request, "state": initial_state}
    )
    _validate_central_inspection(
        central_before, state=initial_state, manifest=manifest
    )
    if first_attempt:
        write_exclusive_bytes_v1(marker_path, canonical_json_bytes(expected_marker))
        copy_small(
            central_alias,
            marker_path,
            marker_path.read_bytes(),
            central_python,
        )
    for inspection in inspections:
        members = [
            str(
                Path(fixed["results_root"]).resolve().relative_to(common)
                / f"worker-{index}"
            )
            for index in inspection["workers"]
        ]
        for index in inspection["workers"]:
            worker = manifest["workers"][index]
            members.extend(
                str(
                    (Path(fixed["status_root"]) / worker[key])
                    .resolve()
                    .relative_to(common)
                )
                for key in (
                    "policy_training_status_stream",
                    "player_evidence_status_stream",
                )
            )
            members.extend(
                str(
                    (
                        Path(fixed["log_root"])
                        / f"worker-{index}-{phase}.log"
                    )
                    .resolve()
                    .relative_to(common)
                )
                for phase in ("training", "evidence")
            )
        transfer(
            inspection["host_alias"],
            {
                "common_root": str(common),
                "tar_members": members,
                "files": inspection["files"],
                "central_host_alias": central_alias,
            },
        )
    central_after = inspect_central(
        central_alias, {**central_request, "state": "COMPLETE"}
    )
    _validate_central_inspection(
        central_after,
        state="COMPLETE",
        manifest=manifest,
        expected_files=expected_files,
    )
    receipt = {
        "schema": SCHEMA_V1,
        "protocol_id": protocol["protocol_id"],
        "source_commit": protocol["source_commit"],
        "central_expected_hostname": manifest["central_analysis"][
            "expected_hostname"
        ],
        "remote_workers": list(REMOTE_WORKERS_V1),
        "transport_method": (
            "LOCAL_CONTROLLER_SSH_SOURCE_TAR_STDOUT_TO_SSH_GPU2_TAR_STDIN"
        ),
        "job_reexecution": False,
        "source_hosts": inspections,
    }
    write_exclusive_bytes_v1(receipt_path, canonical_json_bytes(receipt))
    copy_small(
        central_alias,
        receipt_path,
        receipt_path.read_bytes(),
        central_python,
    )
    return receipt


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--history-scan-receipt", type=Path)
    parser.add_argument("--source-inspect-only", action="store_true")
    parser.add_argument("--central-inspect-only", action="store_true")
    parser.add_argument("--central-state", choices=("FIRST", "RETRY", "COMPLETE"))
    parser.add_argument("--workers")
    return parser.parse_args()


def main() -> int:
    args = _arguments()
    try:
        protocol = validate_ratified_learned_resource_forecast_protocol_v1(
            _read_object(args.protocol, "ratified U002 protocol")
        )
        manifest = _read_object(args.manifest, "U002 launch manifest")
        prepare = _load_prepare_module()
        if manifest != prepare.build_launch_manifest_v1(protocol):
            raise LearnedResourceForecastGatherV1Error(
                "launch manifest does not replay from the ratified protocol"
            )
        if args.source_inspect_only:
            if not args.workers:
                raise LearnedResourceForecastGatherV1Error(
                    "source inspection requires exact worker indices"
                )
            workers = [int(value) for value in args.workers.split(",")]
            print(json.dumps(_inspect_local_source(protocol, manifest, workers), sort_keys=True))
            return 0
        if args.central_inspect_only:
            if args.central_state is None:
                raise LearnedResourceForecastGatherV1Error(
                    "central inspection requires its gather state"
                )
            print(
                json.dumps(
                    _inspect_central_local(protocol, manifest, args.central_state),
                    sort_keys=True,
                )
            )
            return 0
        if args.history_scan_receipt is None:
            raise LearnedResourceForecastGatherV1Error(
                "central gather requires the history-scan receipt"
            )
        receipt = _gather(
            protocol_path=args.protocol,
            manifest_path=args.manifest,
            history_path=args.history_scan_receipt,
        )
    except (
        LearnedResourceForecastGatherV1Error,
        LearnedResourceForecastProtocolV1Error,
        ScienceExecutionIOV1Error,
    ) as error:
        raise SystemExit(str(error)) from error
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
