#!/usr/bin/env python3
"""Gather U002 training and U004 evidence to gpu2 without rerunning jobs."""

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
from acfqp.science.learned_resource_forecast_evidence_successor_protocol_v1 import (
    LearnedResourceForecastEvidenceSuccessorProtocolV1Error,
    validate_ratified_learned_resource_forecast_evidence_successor_protocol_v1,
)
from acfqp.science.learned_resource_forecast_protocol_v1 import (
    LearnedResourceForecastProtocolV1Error,
    validate_ratified_learned_resource_forecast_protocol_v1,
)


REPOSITORY = Path(__file__).resolve().parents[1]
SCHEMA_V1 = (
    "acfqp.science.learned_resource_forecast_dual_authority_gather.u004.v1"
)
MARKER_SCHEMA_V1 = (
    "acfqp.science.learned_resource_forecast_dual_authority_gather_marker.u004.v1"
)
REMOTE_WORKERS_V1 = (2, 3, 4, 5)
SSH_NO_MUX_OPTIONS_V1 = (
    "-o",
    "BatchMode=yes",
    "-o",
    "ControlMaster=no",
    "-o",
    "ControlPath=none",
)
SourceInspectorV1 = Callable[[str, dict[str, Any]], dict[str, Any]]
TransporterV1 = Callable[[str, dict[str, Any]], None]
CentralInspectorV1 = Callable[[str, dict[str, Any]], dict[str, Any]]
SmallFileCopierV1 = Callable[[str, Path, bytes, str], None]


class LearnedResourceForecastGatherU004V1Error(RuntimeError):
    """The dual-authority transport or its exact receipt is invalid."""


def _load_script(name: str, filename: str):
    path = REPOSITORY / "scripts" / filename
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise LearnedResourceForecastGatherU004V1Error(
            f"cannot load U004 gather dependency: {path}"
        )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _predecessor_prepare_module():
    return _load_script(
        "acfqp_u002_prepare_for_u004_gather",
        "prepare_learned_resource_forecast_campaign_u002.py",
    )


def _successor_prepare_module():
    return _load_script(
        "acfqp_u004_prepare_for_u004_gather",
        "prepare_learned_resource_forecast_evidence_successor_u004.py",
    )


def _history_module():
    return _load_script(
        "acfqp_u004_history_for_u004_gather",
        "scan_learned_resource_forecast_history_u004.py",
    )


def _postprocess_module():
    return _load_script(
        "acfqp_u004_postprocess_for_u004_gather",
        "postprocess_retain_learned_resource_forecast_u004.py",
    )


def _read_object(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise LearnedResourceForecastGatherU004V1Error(
            f"cannot read {label}: {path}"
        ) from error
    if type(value) is not dict:
        raise LearnedResourceForecastGatherU004V1Error(
            f"{label} must contain one JSON object"
        )
    return value


def _validate_authorities(
    predecessor_protocol: dict[str, Any],
    successor_protocol: dict[str, Any],
    predecessor_manifest: dict[str, Any],
    successor_manifest: dict[str, Any],
) -> None:
    if predecessor_manifest != _predecessor_prepare_module().build_launch_manifest_v1(
        predecessor_protocol
    ):
        raise LearnedResourceForecastGatherU004V1Error(
            "U002 predecessor manifest does not replay"
        )
    if successor_manifest != _successor_prepare_module().build_launch_manifest_v1(
        successor_protocol
    ):
        raise LearnedResourceForecastGatherU004V1Error(
            "U004 successor manifest does not replay"
        )
    authority = successor_protocol["predecessor_training_authority"]
    if (
        authority.get("protocol_id") != predecessor_protocol["protocol_id"]
        or authority.get("source_commit") != predecessor_protocol["source_commit"]
        or authority.get("pilot_execution_identity")
        != predecessor_protocol["pilot_execution_identity"]
        or authority.get("training_artifacts_are_read_only_inputs") is not True
        or authority.get("training_artifacts_may_be_relabelled_as_u004") is not False
        or authority.get("model_evaluation_tape_prefix")
        != predecessor_protocol["evaluation_tape_prefix"]
        or authority.get("model_evaluation_measurements_are_read_only_inputs")
        is not True
        or authority.get("model_evaluation_reexecuted_in_u004") is not False
        or successor_protocol["evaluation_tape_prefix"]
        != predecessor_protocol["evaluation_tape_prefix"]
        or authority.get("failed_u002_evidence_dispatch_eligible") is not False
        or successor_manifest.get("phase_roster") != ["evidence"]
        or successor_manifest.get("predecessor_training_authority") != authority
    ):
        raise LearnedResourceForecastGatherU004V1Error(
            "U002/U004 authority boundary changed"
        )


def _common_root(
    predecessor_manifest: dict[str, Any], successor_manifest: dict[str, Any]
) -> Path:
    old_fixed = predecessor_manifest["fixed_paths"]
    new_fixed = successor_manifest["fixed_paths"]
    parents = {
        Path(fixed[key]).resolve().parent
        for fixed in (old_fixed, new_fixed)
        for key in ("results_root", "status_root", "log_root")
    }
    if len(parents) != 1:
        raise LearnedResourceForecastGatherU004V1Error(
            "dual-authority roots no longer share one server-side parent"
        )
    return parents.pop()


def _worker_file_paths(
    predecessor_manifest: dict[str, Any],
    successor_manifest: dict[str, Any],
    worker_index: int,
) -> list[Path]:
    old_fixed = predecessor_manifest["fixed_paths"]
    new_fixed = successor_manifest["fixed_paths"]
    old_worker = predecessor_manifest["workers"][worker_index]
    new_worker = successor_manifest["workers"][worker_index]
    old_root = Path(old_fixed["results_root"]) / f"worker-{worker_index}"
    new_root = Path(new_fixed["results_root"]) / f"worker-{worker_index}"
    old_names = [
        name
        for job in old_worker["policy_training_jobs"]
        for name in (job["result_filename"], *job["checkpoint_filenames"])
    ]
    new_names: list[str] = []
    for job in new_worker["player_evidence_jobs"]:
        new_names.extend((job["label_filename"], job["probe_filename"]))
        if job["split"] == "TRAIN":
            new_names.extend(
                (job["trajectory_metadata_filename"], job["trajectory_array_filename"])
            )
    paths = [old_root / name for name in old_names]
    paths.extend(new_root / name for name in new_names)
    paths.extend(
        (
            Path(old_fixed["status_root"])
            / old_worker["policy_training_status_stream"],
            Path(old_fixed["log_root"]) / f"worker-{worker_index}-training.log",
            Path(new_fixed["status_root"])
            / new_worker["player_evidence_status_stream"],
            Path(new_fixed["log_root"]) / f"worker-{worker_index}-evidence.log",
        )
    )
    expected = 352 if new_worker["train_seed_count"] == 6 else 334
    if len(paths) != expected or len(set(paths)) != expected:
        raise LearnedResourceForecastGatherU004V1Error(
            "dual-authority worker file roster changed"
        )
    return paths


def _host_workers(successor_manifest: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for host_alias in ("jtl110gpu", "jtl311linux"):
        workers = [
            worker["worker"]
            for worker in successor_manifest["workers"]
            if worker["host_alias"] == host_alias
        ]
        if len(workers) != 2 or any(index not in REMOTE_WORKERS_V1 for index in workers):
            raise LearnedResourceForecastGatherU004V1Error(
                "remote worker ownership differs from the U004 manifest"
            )
        first = successor_manifest["workers"][workers[0]]
        rows.append(
            {
                "host_alias": host_alias,
                "expected_hostname": first["expected_hostname"],
                "python": first["python"],
                "workers": workers,
            }
        )
    return rows


def _validate_worker_closure(
    predecessor_manifest: dict[str, Any],
    successor_manifest: dict[str, Any],
    worker_index: int,
) -> None:
    postprocess = _postprocess_module()
    old_fixed = predecessor_manifest["fixed_paths"]
    new_fixed = successor_manifest["fixed_paths"]
    old_worker = predecessor_manifest["workers"][worker_index]
    new_worker = successor_manifest["workers"][worker_index]
    old_root = Path(old_fixed["results_root"]) / f"worker-{worker_index}"
    new_root = Path(new_fixed["results_root"]) / f"worker-{worker_index}"
    postprocess._require_exact_directory(
        old_root,
        set(postprocess._predecessor_artifact_map(old_worker)),
        f"U002 worker-{worker_index} training directory",
    )
    postprocess._require_exact_directory(
        new_root,
        set(postprocess._successor_artifact_map(new_worker)),
        f"U004 worker-{worker_index} evidence directory",
    )
    postprocess._validate_worker_status(
        Path(old_fixed["status_root"])
        / old_worker["policy_training_status_stream"],
        phase="training",
        worker_index=worker_index,
        jobs=old_worker["policy_training_jobs"],
    )
    postprocess._validate_worker_log(
        Path(old_fixed["log_root"]) / f"worker-{worker_index}-training.log",
        phase="training",
        worker_index=worker_index,
        expected_count=24,
        results_root=old_root,
    )
    postprocess._validate_worker_status(
        Path(new_fixed["status_root"])
        / new_worker["player_evidence_status_stream"],
        phase="evidence",
        worker_index=worker_index,
        jobs=new_worker["player_evidence_jobs"],
    )
    postprocess._validate_worker_log(
        Path(new_fixed["log_root"]) / f"worker-{worker_index}-evidence.log",
        phase="evidence",
        worker_index=worker_index,
        expected_count=72,
        results_root=new_root,
    )


def _inspect_local_source(
    predecessor_protocol: dict[str, Any],
    successor_protocol: dict[str, Any],
    predecessor_manifest: dict[str, Any],
    successor_manifest: dict[str, Any],
    worker_indices: list[int],
) -> dict[str, Any]:
    del predecessor_protocol
    if bound_clean_source_commit_v1(REPOSITORY) != successor_protocol["source_commit"]:
        raise LearnedResourceForecastGatherU004V1Error(
            "remote U004 gather source commit changed"
        )
    expected_hostname = successor_manifest["workers"][worker_indices[0]][
        "expected_hostname"
    ]
    if socket.gethostname() != expected_hostname:
        raise LearnedResourceForecastGatherU004V1Error(
            "remote gather source hostname changed"
        )
    for index in worker_indices:
        if (
            index not in REMOTE_WORKERS_V1
            or successor_manifest["workers"][index]["expected_hostname"]
            != expected_hostname
            or predecessor_manifest["workers"][index]["expected_hostname"]
            != expected_hostname
        ):
            raise LearnedResourceForecastGatherU004V1Error(
                "remote gather source worker ownership changed"
            )
        _validate_worker_closure(
            predecessor_manifest, successor_manifest, index
        )
    common = _common_root(predecessor_manifest, successor_manifest)
    files = []
    for index in worker_indices:
        for path in _worker_file_paths(
            predecessor_manifest, successor_manifest, index
        ):
            if not path.is_file():
                raise LearnedResourceForecastGatherU004V1Error(
                    f"remote source file disappeared: {path}"
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
        "predecessor_training_artifacts_relabelled": False,
        "failed_u002_evidence_dispatch_used": False,
    }


def _ssh_source_inspector(host_alias: str, request: dict[str, Any]) -> dict[str, Any]:
    command = shlex.join(
        [
            "env",
            f"PYTHONPATH={request['source_pythonpath']}",
            request["python"],
            str(REPOSITORY / "scripts/gather_learned_resource_forecast_evidence_u004.py"),
            "--source-inspect-only",
            "--predecessor-protocol",
            request["predecessor_protocol"],
            "--predecessor-manifest",
            request["predecessor_manifest"],
            "--protocol",
            request["protocol"],
            "--manifest",
            request["manifest"],
            "--workers",
            ",".join(str(value) for value in request["workers"]),
        ]
    )
    completed = subprocess.run(
        ["ssh", *SSH_NO_MUX_OPTIONS_V1, host_alias, command],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise LearnedResourceForecastGatherU004V1Error(
            f"remote source inspection failed on {host_alias}: "
            f"{completed.stderr.strip()}"
        )
    try:
        value = json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        raise LearnedResourceForecastGatherU004V1Error(
            f"remote source inspection on {host_alias} returned no JSON"
        ) from error
    if type(value) is not dict:
        raise LearnedResourceForecastGatherU004V1Error(
            "remote source inspection returned a non-object"
        )
    return value


def _tar_stream_transport(host_alias: str, request: dict[str, Any]) -> None:
    remote = subprocess.Popen(
        [
            "ssh",
            *SSH_NO_MUX_OPTIONS_V1,
            host_alias,
            "tar",
            "-C",
            request["common_root"],
            "-cf",
            "-",
            "--",
            *request["tar_members"],
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert remote.stdout is not None
    central = subprocess.run(
        [
            "ssh",
            *SSH_NO_MUX_OPTIONS_V1,
            request["central_host_alias"],
            "tar",
            "-C",
            request["common_root"],
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
    if remote_returncode != 0 or central.returncode != 0:
        raise LearnedResourceForecastGatherU004V1Error(
            "server-to-server dual-authority tar stream failed: "
            + remote_stderr.decode(errors="replace").strip()
            + " "
            + central.stderr.decode(errors="replace").strip()
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
    completed = subprocess.run(
        [
            "ssh",
            *SSH_NO_MUX_OPTIONS_V1,
            host_alias,
            shlex.join([python_path, "-c", program, str(path)]),
        ],
        input=raw,
        check=False,
        capture_output=True,
    )
    if completed.returncode != 0:
        raise LearnedResourceForecastGatherU004V1Error(
            f"small authority copy failed for {path}: "
            + completed.stderr.decode(errors="replace").strip()
        )


def _root_state(
    root: Path, *, allowed: tuple[int, ...], required: tuple[int, ...], label: str
) -> None:
    if not root.is_dir():
        raise LearnedResourceForecastGatherU004V1Error(f"{label} is not a directory")
    entries = tuple(root.iterdir())
    names = {path.name for path in entries}
    allowed_names = {f"worker-{index}" for index in allowed}
    required_names = {f"worker-{index}" for index in required}
    if (
        any(not path.is_dir() for path in entries)
        or not names.issubset(allowed_names)
        or not required_names.issubset(names)
    ):
        raise LearnedResourceForecastGatherU004V1Error(
            f"{label} differs from its gather state"
        )


def _flat_root_state(
    root: Path, *, allowed: set[str], required: set[str], label: str
) -> None:
    if not root.is_dir():
        raise LearnedResourceForecastGatherU004V1Error(f"{label} is not a directory")
    entries = tuple(root.iterdir())
    names = {path.name for path in entries}
    if (
        any(not path.is_file() for path in entries)
        or not names.issubset(allowed)
        or not required.issubset(names)
    ):
        raise LearnedResourceForecastGatherU004V1Error(
            f"{label} differs from its gather state"
        )


def _validate_dispatches(
    predecessor_manifest: dict[str, Any], successor_manifest: dict[str, Any]
) -> None:
    postprocess = _postprocess_module()
    old_fixed = predecessor_manifest["fixed_paths"]
    new_fixed = successor_manifest["fixed_paths"]
    postprocess._validate_dispatch_status(
        Path(old_fixed["training_dispatch_status"]),
        phase="training",
        manifest=predecessor_manifest,
        fixed=old_fixed,
        successor=False,
    )
    postprocess._validate_dispatch_status(
        Path(new_fixed["evidence_dispatch_status"]),
        phase="evidence",
        manifest=successor_manifest,
        fixed=new_fixed,
        successor=True,
    )
    postprocess._validate_ineligible_failed_dispatch(
        Path(new_fixed["ineligible_predecessor_evidence_dispatch_status"])
    )


def _inspect_central_local(
    predecessor_protocol: dict[str, Any],
    successor_protocol: dict[str, Any],
    predecessor_manifest: dict[str, Any],
    successor_manifest: dict[str, Any],
    state: str,
) -> dict[str, Any]:
    del predecessor_protocol
    if state not in {"FIRST", "RETRY", "COMPLETE"}:
        raise LearnedResourceForecastGatherU004V1Error("unknown central gather state")
    if (
        bound_clean_source_commit_v1(REPOSITORY) != successor_protocol["source_commit"]
        or socket.gethostname()
        != successor_manifest["central_analysis"]["expected_hostname"]
    ):
        raise LearnedResourceForecastGatherU004V1Error(
            "central gather source or hostname changed"
        )
    old_fixed = predecessor_manifest["fixed_paths"]
    new_fixed = successor_manifest["fixed_paths"]
    local = (0, 1)
    allowed = local if state == "FIRST" else tuple(range(6))
    required = allowed if state in {"FIRST", "COMPLETE"} else local
    _root_state(
        Path(old_fixed["results_root"]),
        allowed=allowed,
        required=required,
        label="central U002 training results",
    )
    _root_state(
        Path(new_fixed["results_root"]),
        allowed=allowed,
        required=required,
        label="central U004 evidence results",
    )
    old_status_all = {
        worker["policy_training_status_stream"]
        for worker in predecessor_manifest["workers"]
    }
    old_status_local = {
        predecessor_manifest["workers"][index]["policy_training_status_stream"]
        for index in local
    }
    old_logs_all = {f"worker-{index}-training.log" for index in range(6)}
    old_logs_local = {f"worker-{index}-training.log" for index in local}
    new_status_all = {
        worker["player_evidence_status_stream"]
        for worker in successor_manifest["workers"]
    }
    new_status_local = {
        successor_manifest["workers"][index]["player_evidence_status_stream"]
        for index in local
    }
    new_logs_all = {f"worker-{index}-evidence.log" for index in range(6)}
    new_logs_local = {f"worker-{index}-evidence.log" for index in local}
    for root, all_names, local_names, label in (
        (Path(old_fixed["status_root"]), old_status_all, old_status_local, "U002 status"),
        (Path(old_fixed["log_root"]), old_logs_all, old_logs_local, "U002 logs"),
        (Path(new_fixed["status_root"]), new_status_all, new_status_local, "U004 status"),
        (Path(new_fixed["log_root"]), new_logs_all, new_logs_local, "U004 logs"),
    ):
        expected_required = all_names if state == "COMPLETE" else local_names
        expected_allowed = local_names if state == "FIRST" else all_names
        _flat_root_state(
            root,
            allowed=expected_allowed,
            required=expected_required,
            label=f"central {label}",
        )
    for index in (tuple(range(6)) if state == "COMPLETE" else local):
        _validate_worker_closure(predecessor_manifest, successor_manifest, index)
    _validate_dispatches(predecessor_manifest, successor_manifest)
    common = _common_root(predecessor_manifest, successor_manifest)
    files = []
    for index in REMOTE_WORKERS_V1:
        for path in _worker_file_paths(
            predecessor_manifest, successor_manifest, index
        ):
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
        "predecessor_training_artifacts_relabelled": False,
        "failed_u002_evidence_dispatch_used": False,
    }


def _ssh_central_inspector(host_alias: str, request: dict[str, Any]) -> dict[str, Any]:
    command = shlex.join(
        [
            "env",
            f"PYTHONPATH={request['source_pythonpath']}",
            request["python"],
            str(REPOSITORY / "scripts/gather_learned_resource_forecast_evidence_u004.py"),
            "--central-inspect-only",
            "--central-state",
            request["state"],
            "--predecessor-protocol",
            request["predecessor_protocol"],
            "--predecessor-manifest",
            request["predecessor_manifest"],
            "--protocol",
            request["protocol"],
            "--manifest",
            request["manifest"],
        ]
    )
    completed = subprocess.run(
        ["ssh", *SSH_NO_MUX_OPTIONS_V1, host_alias, command],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise LearnedResourceForecastGatherU004V1Error(
            "central gather inspection failed: " + completed.stderr.strip()
        )
    try:
        value = json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        raise LearnedResourceForecastGatherU004V1Error(
            "central gather inspection returned no JSON"
        ) from error
    if type(value) is not dict:
        raise LearnedResourceForecastGatherU004V1Error(
            "central gather inspection returned a non-object"
        )
    return value


def _marker(
    predecessor_protocol: dict[str, Any],
    successor_protocol: dict[str, Any],
    successor_manifest: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema": MARKER_SCHEMA_V1,
        "predecessor_protocol_id": predecessor_protocol["protocol_id"],
        "predecessor_source_commit": predecessor_protocol["source_commit"],
        "predecessor_pilot_execution_identity": predecessor_protocol[
            "pilot_execution_identity"
        ],
        "successor_protocol_id": successor_protocol["protocol_id"],
        "successor_source_commit": successor_protocol["source_commit"],
        "successor_pilot_execution_identity": successor_protocol[
            "pilot_execution_identity"
        ],
        "central_host_alias": successor_manifest["central_analysis"]["host_alias"],
        "central_expected_hostname": successor_manifest["central_analysis"][
            "expected_hostname"
        ],
        "remote_workers": list(REMOTE_WORKERS_V1),
        "transport_is_not_job_execution": True,
        "transport_retry_may_only_overwrite_registered_destination_files": True,
        "model_evaluation_tape_prefix": predecessor_protocol[
            "evaluation_tape_prefix"
        ],
        "model_evaluation_provenance": "READ_ONLY_U002_PREDECESSOR",
        "model_evaluation_reexecuted_in_u004": False,
        "predecessor_training_artifacts_relabelled": False,
        "failed_u002_evidence_dispatch_used": False,
    }


def _validate_inspection(
    row: dict[str, Any],
    expected: dict[str, Any],
    predecessor_manifest: dict[str, Any],
    successor_manifest: dict[str, Any],
) -> list[dict[str, Any]]:
    common = _common_root(predecessor_manifest, successor_manifest)
    expected_paths = {
        path.resolve().relative_to(common).as_posix()
        for index in expected["workers"]
        for path in _worker_file_paths(
            predecessor_manifest, successor_manifest, index
        )
    }
    files = row.get("files")
    if (
        row.get("host_alias") != expected["host_alias"]
        or row.get("expected_hostname") != expected["expected_hostname"]
        or row.get("actual_hostname") != expected["expected_hostname"]
        or row.get("workers") != expected["workers"]
        or row.get("job_reexecution") is not False
        or row.get("predecessor_training_artifacts_relabelled") is not False
        or row.get("failed_u002_evidence_dispatch_used") is not False
        or type(files) is not list
        or len(files) != len(expected_paths)
        or {file.get("relative_path") for file in files} != expected_paths
        or any(
            type(file.get("size_bytes")) is not int or file["size_bytes"] < 0
            for file in files
        )
    ):
        raise LearnedResourceForecastGatherU004V1Error(
            "remote source inspection differs from the exact dual roster"
        )
    return files


def _validate_central_inspection(
    row: dict[str, Any],
    *,
    state: str,
    successor_manifest: dict[str, Any],
    expected_files: list[dict[str, Any]] | None = None,
) -> None:
    files = row.get("files")
    if (
        row.get("actual_hostname")
        != successor_manifest["central_analysis"]["expected_hostname"]
        or row.get("state") != state
        or row.get("job_reexecution") is not False
        or row.get("predecessor_training_artifacts_relabelled") is not False
        or row.get("failed_u002_evidence_dispatch_used") is not False
        or type(files) is not list
        or len({file.get("relative_path") for file in files}) != len(files)
        or any(
            type(file.get("relative_path")) is not str
            or type(file.get("size_bytes")) is not int
            or file["size_bytes"] < 0
            for file in files
        )
    ):
        raise LearnedResourceForecastGatherU004V1Error(
            "central inspector returned a foreign dual gather state"
        )
    if state == "FIRST" and files:
        raise LearnedResourceForecastGatherU004V1Error(
            "central first state already contains remote worker files"
        )
    if expected_files is not None and {
        (file["relative_path"], file["size_bytes"]) for file in files
    } != {
        (file["relative_path"], file["size_bytes"]) for file in expected_files
    }:
        raise LearnedResourceForecastGatherU004V1Error(
            "central gathered sizes differ from source inspections"
        )


def _validate_receipt_structure(
    receipt: dict[str, Any],
    predecessor_protocol: dict[str, Any],
    successor_protocol: dict[str, Any],
    predecessor_manifest: dict[str, Any],
    successor_manifest: dict[str, Any],
) -> list[dict[str, Any]]:
    hosts = receipt.get("source_hosts")
    if (
        receipt.get("schema") != SCHEMA_V1
        or receipt.get("predecessor_protocol_id")
        != predecessor_protocol["protocol_id"]
        or receipt.get("predecessor_source_commit")
        != predecessor_protocol["source_commit"]
        or receipt.get("predecessor_pilot_execution_identity")
        != predecessor_protocol["pilot_execution_identity"]
        or receipt.get("successor_protocol_id") != successor_protocol["protocol_id"]
        or receipt.get("successor_source_commit") != successor_protocol["source_commit"]
        or receipt.get("successor_pilot_execution_identity")
        != successor_protocol["pilot_execution_identity"]
        or receipt.get("central_expected_hostname")
        != successor_manifest["central_analysis"]["expected_hostname"]
        or receipt.get("remote_workers") != list(REMOTE_WORKERS_V1)
        or receipt.get("transport_method")
        != "LOCAL_CONTROLLER_SSH_DUAL_TREE_TAR_TO_SSH_GPU2_TAR"
        or receipt.get("job_reexecution") is not False
        or receipt.get("model_evaluation_tape_prefix")
        != predecessor_protocol["evaluation_tape_prefix"]
        or receipt.get("model_evaluation_provenance")
        != "READ_ONLY_U002_PREDECESSOR"
        or receipt.get("model_evaluation_reexecuted_in_u004") is not False
        or receipt.get("predecessor_training_artifacts_relabelled") is not False
        or receipt.get("failed_u002_evidence_dispatch_used") is not False
        or type(hosts) is not list
        or len(hosts) != 2
    ):
        raise LearnedResourceForecastGatherU004V1Error(
            "gather receipt differs from its dual-authority contract"
        )
    normalized = []
    for row, expected in zip(hosts, _host_workers(successor_manifest), strict=True):
        files = _validate_inspection(
            row, expected, predecessor_manifest, successor_manifest
        )
        normalized.append({**row, "files": files})
    return normalized


def _validate_central_files(
    inspections: list[dict[str, Any]],
    predecessor_manifest: dict[str, Any],
    successor_manifest: dict[str, Any],
) -> None:
    common = _common_root(predecessor_manifest, successor_manifest)
    for inspection in inspections:
        for file in inspection["files"]:
            path = common / file["relative_path"]
            if not path.is_file() or path.stat().st_size != file["size_bytes"]:
                raise LearnedResourceForecastGatherU004V1Error(
                    "central gathered file is missing or size-incomplete"
                )
    for index in REMOTE_WORKERS_V1:
        _validate_worker_closure(predecessor_manifest, successor_manifest, index)


def validate_gather_receipt_v1(
    receipt: dict[str, Any],
    predecessor_protocol: dict[str, Any],
    successor_protocol: dict[str, Any],
    predecessor_manifest: dict[str, Any],
    successor_manifest: dict[str, Any],
) -> dict[str, Any]:
    """Validate the exact U002-training/U004-evidence gather receipt."""

    _validate_authorities(
        predecessor_protocol,
        successor_protocol,
        predecessor_manifest,
        successor_manifest,
    )
    fixed = successor_manifest["fixed_paths"]
    marker = _read_object(Path(fixed["gather_transport_marker"]), "gather marker")
    if marker != _marker(
        predecessor_protocol, successor_protocol, successor_manifest
    ):
        raise LearnedResourceForecastGatherU004V1Error(
            "gather marker differs from its fixed dual transport identity"
        )
    normalized = _validate_receipt_structure(
        receipt,
        predecessor_protocol,
        successor_protocol,
        predecessor_manifest,
        successor_manifest,
    )
    _validate_central_files(
        normalized, predecessor_manifest, successor_manifest
    )
    return receipt


def _transport_members(
    predecessor_manifest: dict[str, Any],
    successor_manifest: dict[str, Any],
    worker_indices: list[int],
) -> list[str]:
    common = _common_root(predecessor_manifest, successor_manifest)
    old_fixed = predecessor_manifest["fixed_paths"]
    new_fixed = successor_manifest["fixed_paths"]
    members = []
    for index in worker_indices:
        old_worker = predecessor_manifest["workers"][index]
        new_worker = successor_manifest["workers"][index]
        for path in (
            Path(old_fixed["results_root"]) / f"worker-{index}",
            Path(new_fixed["results_root"]) / f"worker-{index}",
            Path(old_fixed["status_root"])
            / old_worker["policy_training_status_stream"],
            Path(old_fixed["log_root"]) / f"worker-{index}-training.log",
            Path(new_fixed["status_root"])
            / new_worker["player_evidence_status_stream"],
            Path(new_fixed["log_root"]) / f"worker-{index}-evidence.log",
        ):
            members.append(path.resolve().relative_to(common).as_posix())
    if len(members) != 6 * len(worker_indices) or len(set(members)) != len(members):
        raise LearnedResourceForecastGatherU004V1Error(
            "dual-tree tar member roster changed"
        )
    return members


def _gather(
    *,
    predecessor_protocol_path: Path,
    predecessor_manifest_path: Path,
    successor_protocol_path: Path,
    successor_manifest_path: Path,
    history_path: Path,
    inspector: SourceInspectorV1 | None = None,
    transporter: TransporterV1 | None = None,
    central_inspector: CentralInspectorV1 | None = None,
    small_file_copier: SmallFileCopierV1 | None = None,
) -> dict[str, Any]:
    predecessor_protocol = validate_ratified_learned_resource_forecast_protocol_v1(
        _read_object(predecessor_protocol_path, "U002 predecessor protocol")
    )
    successor_protocol = (
        validate_ratified_learned_resource_forecast_evidence_successor_protocol_v1(
            _read_object(successor_protocol_path, "U004 successor protocol")
        )
    )
    predecessor_manifest = _read_object(
        predecessor_manifest_path, "U002 predecessor manifest"
    )
    successor_manifest = _read_object(
        successor_manifest_path, "U004 successor manifest"
    )
    _validate_authorities(
        predecessor_protocol,
        successor_protocol,
        predecessor_manifest,
        successor_manifest,
    )
    fixed = successor_manifest["fixed_paths"]
    if (
        bound_clean_source_commit_v1(REPOSITORY) != successor_protocol["source_commit"]
        or REPOSITORY.resolve() != Path(fixed["source_checkout"]).resolve()
        or predecessor_protocol_path.resolve()
        != Path(fixed["predecessor_protocol"]).resolve()
        or predecessor_manifest_path.resolve()
        != Path(fixed["predecessor_manifest"]).resolve()
        or successor_protocol_path.resolve() != Path(fixed["protocol"]).resolve()
        or successor_manifest_path.resolve() != Path(fixed["manifest"]).resolve()
        or history_path.resolve() != Path(fixed["history_scan_receipt"]).resolve()
    ):
        raise LearnedResourceForecastGatherU004V1Error(
            "gather controller source or authority paths changed"
        )
    _history_module().validate_history_scan_receipt_v1(
        _read_object(history_path, "U004 history receipt"),
        successor_protocol,
        successor_manifest,
    )
    _validate_dispatches(predecessor_manifest, successor_manifest)

    central_alias = successor_manifest["central_analysis"]["host_alias"]
    central_python = successor_manifest["workers"][0]["python"]
    copy_small = small_file_copier or _copy_small_to_remote
    authority_paths = (
        predecessor_protocol_path,
        predecessor_manifest_path,
        successor_protocol_path,
        successor_manifest_path,
        history_path,
        Path(fixed["predecessor_training_dispatch_status"]),
        Path(fixed["ineligible_predecessor_evidence_dispatch_status"]),
        Path(fixed["evidence_dispatch_status"]),
    )
    for path in authority_paths:
        if not path.is_file():
            raise LearnedResourceForecastGatherU004V1Error(
                f"small dual authority is missing: {path}"
            )
        copy_small(central_alias, path, path.read_bytes(), central_python)

    marker_path = Path(fixed["gather_transport_marker"])
    receipt_path = Path(fixed["gather_receipt"])
    expected_marker = _marker(
        predecessor_protocol, successor_protocol, successor_manifest
    )
    first_attempt = not marker_path.exists()
    if not first_attempt and _read_object(marker_path, "gather marker") != expected_marker:
        raise LearnedResourceForecastGatherU004V1Error(
            "existing gather marker belongs to another transport"
        )
    if not first_attempt:
        copy_small(
            central_alias, marker_path, marker_path.read_bytes(), central_python
        )

    inspect = inspector or _ssh_source_inspector
    inspections = []
    for expected in _host_workers(successor_manifest):
        request = {
            "predecessor_protocol": str(predecessor_protocol_path),
            "predecessor_manifest": str(predecessor_manifest_path),
            "protocol": str(successor_protocol_path),
            "manifest": str(successor_manifest_path),
            "source_pythonpath": successor_manifest["source_pythonpath"],
            "python": expected["python"],
            "workers": expected["workers"],
        }
        inspected = inspect(expected["host_alias"], request)
        row = {
            "host_alias": expected["host_alias"],
            "expected_hostname": expected["expected_hostname"],
            **inspected,
        }
        files = _validate_inspection(
            row, expected, predecessor_manifest, successor_manifest
        )
        inspections.append({**row, "files": files})
    expected_files = [file for row in inspections for file in row["files"]]
    if len(expected_files) != 4 * 334:
        raise LearnedResourceForecastGatherU004V1Error(
            "remote gather roster no longer contains exactly 1336 files"
        )
    central_request = {
        "predecessor_protocol": str(predecessor_protocol_path),
        "predecessor_manifest": str(predecessor_manifest_path),
        "protocol": str(successor_protocol_path),
        "manifest": str(successor_manifest_path),
        "source_pythonpath": successor_manifest["source_pythonpath"],
        "python": central_python,
    }
    inspect_central = central_inspector or _ssh_central_inspector
    if receipt_path.exists():
        if first_attempt:
            raise LearnedResourceForecastGatherU004V1Error(
                "gather receipt exists without its transport marker"
            )
        receipt = _read_object(receipt_path, "gather receipt")
        if _validate_receipt_structure(
            receipt,
            predecessor_protocol,
            successor_protocol,
            predecessor_manifest,
            successor_manifest,
        ) != inspections:
            raise LearnedResourceForecastGatherU004V1Error(
                "existing receipt differs from fresh source inspection"
            )
        central = inspect_central(
            central_alias, {**central_request, "state": "COMPLETE"}
        )
        _validate_central_inspection(
            central,
            state="COMPLETE",
            successor_manifest=successor_manifest,
            expected_files=expected_files,
        )
        copy_small(
            central_alias, receipt_path, receipt_path.read_bytes(), central_python
        )
        return receipt

    state = "FIRST" if first_attempt else "RETRY"
    central_before = inspect_central(
        central_alias, {**central_request, "state": state}
    )
    _validate_central_inspection(
        central_before, state=state, successor_manifest=successor_manifest
    )
    if first_attempt:
        write_exclusive_bytes_v1(marker_path, canonical_json_bytes(expected_marker))
        copy_small(
            central_alias, marker_path, marker_path.read_bytes(), central_python
        )
    transfer = transporter or _tar_stream_transport
    common = _common_root(predecessor_manifest, successor_manifest)
    for inspection in inspections:
        transfer(
            inspection["host_alias"],
            {
                "common_root": str(common),
                "tar_members": _transport_members(
                    predecessor_manifest,
                    successor_manifest,
                    inspection["workers"],
                ),
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
        successor_manifest=successor_manifest,
        expected_files=expected_files,
    )
    receipt = {
        "schema": SCHEMA_V1,
        "predecessor_protocol_id": predecessor_protocol["protocol_id"],
        "predecessor_source_commit": predecessor_protocol["source_commit"],
        "predecessor_pilot_execution_identity": predecessor_protocol[
            "pilot_execution_identity"
        ],
        "successor_protocol_id": successor_protocol["protocol_id"],
        "successor_source_commit": successor_protocol["source_commit"],
        "successor_pilot_execution_identity": successor_protocol[
            "pilot_execution_identity"
        ],
        "central_expected_hostname": successor_manifest["central_analysis"][
            "expected_hostname"
        ],
        "remote_workers": list(REMOTE_WORKERS_V1),
        "transport_method": "LOCAL_CONTROLLER_SSH_DUAL_TREE_TAR_TO_SSH_GPU2_TAR",
        "job_reexecution": False,
        "model_evaluation_tape_prefix": predecessor_protocol[
            "evaluation_tape_prefix"
        ],
        "model_evaluation_provenance": "READ_ONLY_U002_PREDECESSOR",
        "model_evaluation_reexecuted_in_u004": False,
        "predecessor_training_artifacts_relabelled": False,
        "failed_u002_evidence_dispatch_used": False,
        "source_hosts": inspections,
    }
    write_exclusive_bytes_v1(receipt_path, canonical_json_bytes(receipt))
    copy_small(
        central_alias, receipt_path, receipt_path.read_bytes(), central_python
    )
    return receipt


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--predecessor-protocol", type=Path, required=True)
    parser.add_argument("--predecessor-manifest", type=Path, required=True)
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
        predecessor_protocol_path = require_path_outside_repository_v1(
            repository=REPOSITORY,
            path=args.predecessor_protocol,
            label="U002 predecessor protocol",
        )
        predecessor_manifest_path = require_path_outside_repository_v1(
            repository=REPOSITORY,
            path=args.predecessor_manifest,
            label="U002 predecessor manifest",
        )
        successor_protocol_path = require_path_outside_repository_v1(
            repository=REPOSITORY, path=args.protocol, label="U004 protocol"
        )
        successor_manifest_path = require_path_outside_repository_v1(
            repository=REPOSITORY, path=args.manifest, label="U004 manifest"
        )
        predecessor_protocol = validate_ratified_learned_resource_forecast_protocol_v1(
            _read_object(predecessor_protocol_path, "U002 predecessor protocol")
        )
        successor_protocol = validate_ratified_learned_resource_forecast_evidence_successor_protocol_v1(
            _read_object(successor_protocol_path, "U004 successor protocol")
        )
        predecessor_manifest = _read_object(
            predecessor_manifest_path, "U002 predecessor manifest"
        )
        successor_manifest = _read_object(
            successor_manifest_path, "U004 successor manifest"
        )
        _validate_authorities(
            predecessor_protocol,
            successor_protocol,
            predecessor_manifest,
            successor_manifest,
        )
        if args.source_inspect_only:
            if not args.workers:
                raise LearnedResourceForecastGatherU004V1Error(
                    "source inspection requires exact worker indices"
                )
            workers = [int(value) for value in args.workers.split(",")]
            summary = _inspect_local_source(
                predecessor_protocol,
                successor_protocol,
                predecessor_manifest,
                successor_manifest,
                workers,
            )
        elif args.central_inspect_only:
            if args.central_state is None:
                raise LearnedResourceForecastGatherU004V1Error(
                    "central inspection requires its gather state"
                )
            summary = _inspect_central_local(
                predecessor_protocol,
                successor_protocol,
                predecessor_manifest,
                successor_manifest,
                args.central_state,
            )
        else:
            if args.history_scan_receipt is None:
                raise LearnedResourceForecastGatherU004V1Error(
                    "central gather requires the U004 history receipt"
                )
            summary = _gather(
                predecessor_protocol_path=predecessor_protocol_path,
                predecessor_manifest_path=predecessor_manifest_path,
                successor_protocol_path=successor_protocol_path,
                successor_manifest_path=successor_manifest_path,
                history_path=require_path_outside_repository_v1(
                    repository=REPOSITORY,
                    path=args.history_scan_receipt,
                    label="U004 history receipt",
                ),
            )
    except (
        LearnedResourceForecastGatherU004V1Error,
        LearnedResourceForecastEvidenceSuccessorProtocolV1Error,
        LearnedResourceForecastProtocolV1Error,
        ScienceExecutionIOV1Error,
        ValueError,
    ) as error:
        raise SystemExit(str(error)) from error
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
