#!/usr/bin/env python3
"""Run, independently verify, and retain the one-shot U005 analysis successor."""

from __future__ import annotations

import argparse
from collections import Counter
import importlib.util
import json
import os
from pathlib import Path
import shutil
import socket
import sys
from types import SimpleNamespace
from typing import Any, NoReturn

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
    U004_PROTOCOL_ID_V1,
    U004_SOURCE_COMMIT_V1,
    validate_ratified_analysis_successor_protocol_v1,
)
from acfqp.science.learned_resource_forecast_evidence_successor_protocol_v1 import (
    validate_ratified_learned_resource_forecast_evidence_successor_protocol_v1,
)
from acfqp.science.learned_resource_forecast_protocol_v1 import (
    validate_ratified_learned_resource_forecast_protocol_v1,
)


REPOSITORY = Path(__file__).resolve().parents[1]
INVENTORY_FILENAME_V1 = "retention-inventory.json"
INVENTORY_SCHEMA_V1 = (
    "acfqp.science.learned_resource_forecast_analysis_successor_retention.u005.v1"
)
SUCCESSOR_RECEIPT_SCHEMA_V1 = (
    "acfqp.science.learned_resource_forecast_analysis_successor_receipt.u005.v1"
)
PROVENANCE_U004_FAILURE_V1 = "FAILED_U004_POSTPROCESS_HISTORY"
PROVENANCE_U005_AUTHORITY_V1 = "FRESH_U005_ANALYSIS_AUTHORITY"
PROVENANCE_U005_ANALYSIS_V1 = "U005_ANALYSIS_DERIVED_FROM_READ_ONLY_AUTHORITIES"
PROVENANCE_U005_STATUS_V1 = "U005_ANALYSIS_POSTPROCESS_STATUS"
EXPECTED_RETAINED_ARTIFACT_COUNT_V1 = 2064
EXPECTED_PHYSICAL_FILE_COUNT_V1 = 2065

ANALYSIS_CATEGORIES_V1 = {
    "aligned-resource-forecast.encoder.pt": "u005_encoder_pt",
    "player-shuffled-resource-forecast.encoder.pt": "u005_encoder_pt",
    "aligned-resource-forecast.receipt.json": "u005_encoder_receipt",
    "player-shuffled-resource-forecast.receipt.json": "u005_encoder_receipt",
    "probe-representation-matrices.npz": "u005_matrix_npz",
    "probe-representation-matrices.metadata.json": "u005_matrix_metadata",
    "pilot-result.json": "u005_pilot_result",
    "independent-verification.json": "u005_independent_verification",
    "analysis-successor-receipt.json": "u005_successor_receipt",
}


class LearnedResourceForecastPostprocessU005Error(RuntimeError):
    """The one-shot U005 analysis, verification, or retention is invalid."""


def _fail(message: str) -> NoReturn:
    raise LearnedResourceForecastPostprocessU005Error(message)


def _load_script(name: str, filename: str):
    path = REPOSITORY / "scripts" / filename
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        _fail(f"cannot load U005 dependency: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_U004_POSTPROCESS = _load_script(
    "acfqp_u004_postprocess_helpers_for_u005",
    "postprocess_retain_learned_resource_forecast_u004.py",
)
_U005_PREPARE = _load_script(
    "acfqp_u005_prepare_for_postprocess",
    "prepare_learned_resource_forecast_analysis_successor_u005.py",
)
_U005_HISTORY = _load_script(
    "acfqp_u005_history_for_postprocess",
    "scan_learned_resource_forecast_analysis_history_u005.py",
)
_U005_ANALYSIS = _load_script(
    "acfqp_u005_analysis_for_postprocess",
    "run_learned_resource_forecast_analysis_u005.py",
)
_U005_VERIFIER = _load_script(
    "acfqp_u005_verifier_for_postprocess",
    "verify_learned_resource_forecast_analysis_u005.py",
)


def _read_object(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise LearnedResourceForecastPostprocessU005Error(
            f"cannot read {label}: {path}"
        ) from error
    if type(value) is not dict:
        _fail(f"{label} must contain one JSON object")
    return value


def _read_jsonl(path: Path, label: str) -> list[dict[str, Any]]:
    try:
        rows = [
            json.loads(line)
            for line in path.read_text(encoding="utf-8").splitlines()
        ]
    except (OSError, json.JSONDecodeError) as error:
        raise LearnedResourceForecastPostprocessU005Error(
            f"cannot read {label}: {path}"
        ) from error
    if not rows or any(type(row) is not dict for row in rows):
        _fail(f"{label} must contain nonempty object JSONL")
    return rows


class _StatusStreamV1:
    def __init__(self, path: Path):
        self.path = path
        self.fd: int | None = None

    def __enter__(self):
        self.path.parent.mkdir(parents=True, exist_ok=False)
        try:
            self.fd = os.open(
                self.path,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC,
                0o600,
            )
        except FileExistsError as error:
            raise LearnedResourceForecastPostprocessU005Error(
                "U005 status exists; analysis identity is consumed"
            ) from error
        return self

    def emit(self, row: dict[str, Any]) -> None:
        if self.fd is None:
            _fail("U005 status stream is closed")
        view = memoryview(canonical_json_bytes(row) + b"\n")
        while view:
            view = view[os.write(self.fd, view) :]
        os.fsync(self.fd)

    def __exit__(self, _type, _value, _traceback) -> None:
        if self.fd is not None:
            os.close(self.fd)
            self.fd = None


def _require_fresh_targets_v1(
    analysis_root: Path, status_root: Path, retained_root: Path
) -> None:
    if analysis_root.exists() or status_root.exists() or retained_root.exists():
        _fail("U005 analysis, status, or retained target exists; identity is consumed")


def expected_category_counts_v1() -> dict[str, int]:
    counts = dict(_U004_POSTPROCESS._preanalysis_expected_counts())  # noqa: SLF001
    counts.update(
        {
            "u004_failed_postprocess_status": 1,
            "u005_protocol": 1,
            "u005_manifest": 1,
            "u005_authority_scan_receipt": 1,
            "u005_encoder_pt": 2,
            "u005_encoder_receipt": 2,
            "u005_matrix_npz": 1,
            "u005_matrix_metadata": 1,
            "u005_pilot_result": 1,
            "u005_independent_verification": 1,
            "u005_successor_receipt": 1,
            "u005_postprocess_status": 1,
        }
    )
    return counts


def expected_provenance_counts_v1() -> dict[str, int]:
    return {
        _U004_POSTPROCESS.PROVENANCE_U002_TRAINING_V1: 591,
        _U004_POSTPROCESS.PROVENANCE_U004_EVIDENCE_V1: 1456,
        _U004_POSTPROCESS.PROVENANCE_GATHER_V1: 2,
        _U004_POSTPROCESS.PROVENANCE_FAILED_U002_EVIDENCE_V1: 1,
        PROVENANCE_U004_FAILURE_V1: 1,
        PROVENANCE_U005_AUTHORITY_V1: 3,
        PROVENANCE_U005_ANALYSIS_V1: 9,
        PROVENANCE_U005_STATUS_V1: 1,
    }


def _validate_failed_u004_boundary(
    path: Path, u004_manifest: dict[str, Any]
) -> None:
    fixed = u004_manifest["fixed_paths"]
    if path.resolve() != Path(fixed["postprocess_status"]).resolve():
        _fail("U004 failed postprocess path changed")
    rows = _read_jsonl(path, "failed U004 postprocess status")
    if (
        [row.get("event") for row in rows]
        != [
            "POSTPROCESS_STARTED",
            "PREREQUISITES_COMPLETED",
            "STAGE_STARTED",
            "POSTPROCESS_FAILED",
        ]
        or rows[0].get("source_commit") != U004_SOURCE_COMMIT_V1
        or rows[0].get("successor_protocol_id") != U004_PROTOCOL_ID_V1
        or rows[1].get("predecessor_training_job_count") != 144
        or rows[1].get("predecessor_model_snapshot_count") != 432
        or rows[1].get("successor_evidence_job_count") != 432
        or rows[2] != {"event": "STAGE_STARTED", "stage": "FIT_ENCODERS"}
        or rows[3].get("failure_kind") != "NameError"
        or rows[3].get("failure_message")
        != "name 'aligned_forecast_examples_v1' is not defined"
    ):
        _fail("U004 failed postprocess is not the exact consumed NameError boundary")
    failed_analysis = Path(fixed["analysis_root"])
    if (
        not failed_analysis.is_dir()
        or list(failed_analysis.iterdir()) != []
        or Path(fixed["retained_root"]).exists()
    ):
        _fail("U004 partial analysis or retention state changed")


def _validate_authorities(args: argparse.Namespace):
    paths = {
        name: require_path_outside_repository_v1(
            repository=REPOSITORY,
            path=getattr(args, name),
            label=name.replace("_", " "),
        )
        for name in (
            "u002_protocol",
            "u002_manifest",
            "u004_protocol",
            "u004_manifest",
            "u004_history_scan_receipt",
            "u004_gather_receipt",
            "u004_failed_postprocess_status",
            "u005_protocol",
            "u005_manifest",
            "u005_authority_scan_receipt",
        )
    }
    u002 = validate_ratified_learned_resource_forecast_protocol_v1(
        _read_object(paths["u002_protocol"], "U002 protocol")
    )
    u004 = validate_ratified_learned_resource_forecast_evidence_successor_protocol_v1(
        _read_object(paths["u004_protocol"], "U004 protocol")
    )
    u005 = validate_ratified_analysis_successor_protocol_v1(
        _read_object(paths["u005_protocol"], "U005 protocol")
    )
    u002_manifest = _read_object(paths["u002_manifest"], "U002 manifest")
    u004_manifest = _read_object(paths["u004_manifest"], "U004 manifest")
    u005_manifest = _read_object(paths["u005_manifest"], "U005 manifest")
    if u002_manifest != _U004_POSTPROCESS._load_predecessor_prepare_module().build_launch_manifest_v1(u002):  # noqa: E501, SLF001
        _fail("U002 manifest does not replay")
    if u004_manifest != _U004_POSTPROCESS._load_successor_prepare_module().build_launch_manifest_v1(u004):  # noqa: E501, SLF001
        _fail("U004 manifest does not replay")
    if u005_manifest != _U005_PREPARE.build_launch_manifest_v1(u005):
        _fail("U005 manifest does not replay")
    _U004_POSTPROCESS._load_history_scan_module().validate_history_scan_receipt_v1(  # noqa: SLF001
        _read_object(paths["u004_history_scan_receipt"], "U004 history receipt"),
        u004,
        u004_manifest,
    )
    _U004_POSTPROCESS._load_gather_module().validate_gather_receipt_v1(  # noqa: SLF001
        _read_object(paths["u004_gather_receipt"], "U004 gather receipt"),
        u002,
        u004,
        u002_manifest,
        u004_manifest,
    )
    _validate_failed_u004_boundary(
        paths["u004_failed_postprocess_status"], u004_manifest
    )
    _U005_HISTORY.validate_authority_scan_receipt_v1(
        _read_object(paths["u005_authority_scan_receipt"], "U005 authority receipt"),
        u005,
        u005_manifest,
    )
    fixed = u005_manifest["fixed_paths"]
    if (
        bound_clean_source_commit_v1(REPOSITORY) != u005["source_commit"]
        or REPOSITORY.resolve() != Path(fixed["source_checkout"]).resolve()
        or socket.gethostname() != "erzhu419-Super-Server"
        or args.analysis_device != "cuda:0"
        or args.verifier_device != "cuda:0"
        or paths["u005_protocol"] != Path(fixed["protocol"]).resolve()
        or paths["u005_manifest"] != Path(fixed["manifest"]).resolve()
        or paths["u005_authority_scan_receipt"]
        != Path(fixed["authority_scan_receipt"]).resolve()
        or u005["predecessor_training_authority"]["protocol_id"]
        != u002["protocol_id"]
        or u005["predecessor_evidence_authority"]["protocol_id"]
        != u004["protocol_id"]
        or u005["frozen_analysis_contract"]
        != {key: u004[key] for key in u005["frozen_analysis_contract"]}
    ):
        _fail("U005 source, host, paths, dual authority, or analysis contract changed")
    return paths, u002, u004, u005, u002_manifest, u004_manifest, u005_manifest


def _analysis_entries(analysis_root: Path):
    actual = {path.name for path in analysis_root.iterdir() if path.is_file()}
    if actual != set(ANALYSIS_OUTPUT_FILENAMES_V1):
        _fail("U005 analysis root does not contain exactly nine outputs")
    return [
        (
            analysis_root / filename,
            category,
            PROVENANCE_U005_ANALYSIS_V1,
            Path("successor-u005/analysis") / filename,
        )
        for filename, category in ANALYSIS_CATEGORIES_V1.items()
    ]


def _copy_retained(
    *,
    entries,
    retained_root: Path,
    u002: dict[str, Any],
    u004: dict[str, Any],
    u005: dict[str, Any],
) -> dict[str, Any]:
    if retained_root.exists():
        _fail("U005 retained root exists; analysis identity is consumed")
    retained_root.mkdir(parents=False)
    rows = []
    for source, category, provenance, relative in entries:
        if not source.is_file():
            _fail(f"U005 retention source disappeared: {source}")
        target = retained_root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            _fail("U005 retention destination collision")
        shutil.copy2(source, target)
        rows.append(
            {
                "category": category,
                "provenance": provenance,
                "source_path": str(source),
                "retained_relative_path": relative.as_posix(),
                "size_bytes": target.stat().st_size,
            }
        )
    category_counts = dict(Counter(row["category"] for row in rows))
    provenance_counts = dict(Counter(row["provenance"] for row in rows))
    expected_categories = expected_category_counts_v1()
    expected_provenance = expected_provenance_counts_v1()
    if (
        category_counts != expected_categories
        or provenance_counts != expected_provenance
        or len(rows) != EXPECTED_RETAINED_ARTIFACT_COUNT_V1
    ):
        _fail("U005 retained category or provenance counts do not close at 2064")
    inventory = {
        "schema": INVENTORY_SCHEMA_V1,
        "u002_training_protocol_id": u002["protocol_id"],
        "u002_training_source_commit": u002["source_commit"],
        "u004_evidence_protocol_id": u004["protocol_id"],
        "u004_evidence_source_commit": u004["source_commit"],
        "u005_analysis_protocol_id": u005["protocol_id"],
        "u005_analysis_source_commit": u005["source_commit"],
        "u005_analysis_execution_id": u005["analysis_execution_id"],
        "authority_mode": (
            "READ_ONLY_U002_TRAINING_PLUS_READ_ONLY_U004_EVIDENCE_"
            "PLUS_FRESH_U005_ANALYSIS"
        ),
        "u004_evidence_reexecuted": False,
        "new_evidence_execution_ids": [],
        "new_tape_roots": [],
        "independent_verification_schema_is_unchanged_u004_numeric_replay": True,
        "independent_verification_artifact_owned_by_u005_runtime": True,
        "category_counts": category_counts,
        "provenance_counts": provenance_counts,
        "retention_complete": True,
        "retained_artifact_count_excluding_inventory": (
            EXPECTED_RETAINED_ARTIFACT_COUNT_V1
        ),
        "physical_file_count_including_inventory": (
            EXPECTED_PHYSICAL_FILE_COUNT_V1
        ),
        "entries": rows,
    }
    write_exclusive_bytes_v1(
        retained_root / INVENTORY_FILENAME_V1, canonical_json_bytes(inventory)
    )
    actual = {
        path.relative_to(retained_root).as_posix()
        for path in retained_root.rglob("*")
        if path.is_file()
    }
    expected = {row["retained_relative_path"] for row in rows} | {
        INVENTORY_FILENAME_V1
    }
    if (
        actual != expected
        or len(actual) != EXPECTED_PHYSICAL_FILE_COUNT_V1
    ):
        _fail("U005 retained physical tree does not close at 2065")
    return inventory


def _run(args: argparse.Namespace) -> dict[str, Any]:
    (
        paths,
        u002,
        u004,
        u005,
        u002_manifest,
        u004_manifest,
        u005_manifest,
    ) = _validate_authorities(args)
    fixed = u005_manifest["fixed_paths"]
    analysis_root = Path(fixed["analysis_root"])
    status_root = Path(fixed["status_root"])
    status_path = Path(fixed["analysis_status"])
    retained_root = Path(fixed["retained_root"])
    _require_fresh_targets_v1(analysis_root, status_root, retained_root)
    _U004_POSTPROCESS._default_runtime_validator(  # noqa: SLF001
        paths["u002_protocol"],
        paths["u002_manifest"],
        paths["u004_protocol"],
        paths["u004_manifest"],
        args.analysis_device,
    )
    training_dirs, evidence_dirs, retention_entries = (
        _U004_POSTPROCESS._validate_prerequisites(  # noqa: SLF001
            predecessor_protocol=u002,
            predecessor_manifest=u002_manifest,
            successor_protocol=u004,
            successor_manifest=u004_manifest,
        )
    )
    old_fixed = u002_manifest["fixed_paths"]
    evidence_fixed = u004_manifest["fixed_paths"]
    common = {
        "predecessor_protocol": paths["u002_protocol"],
        "predecessor_manifest": paths["u002_manifest"],
        "protocol": paths["u004_protocol"],
        "manifest": paths["u004_manifest"],
        "u005_protocol": paths["u005_protocol"],
        "u005_manifest": paths["u005_manifest"],
        "device": args.analysis_device,
    }
    with _StatusStreamV1(status_path) as status:
        status.emit(
            {
                "event": "ANALYSIS_SUCCESSOR_STARTED",
                "analysis_execution_id": u005["analysis_execution_id"],
                "analysis_runtime_protocol_id": u005["protocol_id"],
                "analysis_runtime_source_commit": u005["source_commit"],
                "measurement_protocol_id": u004["protocol_id"],
                "measurement_source_commit": u004["source_commit"],
                "host": socket.gethostname(),
                "new_evidence_execution_ids": [],
                "new_tape_roots": [],
            }
        )
        try:
            analysis_root.mkdir(parents=False)
            stages = [
                (
                    "FIT_ENCODERS",
                    SimpleNamespace(
                        operation="fit-encoders",
                        trajectory_dir=evidence_dirs,
                        output_dir=analysis_root,
                        **common,
                    ),
                ),
                (
                    "ENCODE_PROBES",
                    SimpleNamespace(
                        operation="encode-probes",
                        probe_dir=evidence_dirs,
                        aligned_encoder=analysis_root / ANALYSIS_OUTPUT_FILENAMES_V1[0],
                        shuffled_encoder=analysis_root / ANALYSIS_OUTPUT_FILENAMES_V1[1],
                        output_dir=analysis_root,
                        **common,
                    ),
                ),
                (
                    "EVALUATE",
                    SimpleNamespace(
                        operation="evaluate",
                        predecessor_status_dir=[Path(old_fixed["status_root"])],
                        status_dir=[Path(evidence_fixed["status_root"])],
                        predecessor_training_result_dir=training_dirs,
                        worker_result_dir=evidence_dirs,
                        matrix=analysis_root / "probe-representation-matrices.npz",
                        matrix_metadata=analysis_root / "probe-representation-matrices.metadata.json",
                        encoder_receipt_dir=analysis_root,
                        label_dir=evidence_dirs,
                        output=analysis_root / "pilot-result.json",
                        **common,
                    ),
                ),
            ]
            for name, stage_args in stages:
                status.emit({"event": "STAGE_STARTED", "stage": name})
                summary = _U005_ANALYSIS._run(stage_args)  # noqa: SLF001
                if summary.get("success") is not True:
                    _fail(f"U005 analysis stage returned no success: {name}")
                status.emit({"event": "STAGE_COMPLETED", "stage": name})
            status.emit({"event": "STAGE_STARTED", "stage": "INDEPENDENT_VERIFIER"})
            verify_args = SimpleNamespace(
                predecessor_protocol=paths["u002_protocol"],
                predecessor_manifest=paths["u002_manifest"],
                protocol=paths["u004_protocol"],
                manifest=paths["u004_manifest"],
                u005_protocol=paths["u005_protocol"],
                u005_manifest=paths["u005_manifest"],
                predecessor_status_dir=[Path(old_fixed["status_root"])],
                status_dir=[Path(evidence_fixed["status_root"])],
                trajectory_dir=evidence_dirs,
                probe_dir=evidence_dirs,
                label_dir=evidence_dirs,
                encoder_dir=analysis_root,
                predecessor_training_result_dir=training_dirs,
                worker_result_dir=evidence_dirs,
                matrix=analysis_root / "probe-representation-matrices.npz",
                matrix_metadata=analysis_root / "probe-representation-matrices.metadata.json",
                result=analysis_root / "pilot-result.json",
                output=analysis_root / "independent-verification.json",
                device=args.verifier_device,
            )
            verification_summary = _U005_VERIFIER._verify(verify_args)  # noqa: SLF001
            if verification_summary.get("success") is not True:
                _fail("U005 independent verifier returned no success")
            status.emit({"event": "STAGE_COMPLETED", "stage": "INDEPENDENT_VERIFIER"})
            result = _read_object(analysis_root / "pilot-result.json", "pilot result")
            verification = _read_object(
                analysis_root / "independent-verification.json",
                "independent verification",
            )
            provenance = {
                "measurement_protocol_id": u004["protocol_id"],
                "measurement_source_commit": u004["source_commit"],
                "analysis_runtime_protocol_id": u005["protocol_id"],
                "analysis_runtime_source_commit": u005["source_commit"],
                "analysis_runtime_execution_id": u005["analysis_execution_id"],
            }
            if any(
                document.get(key) != value
                for document in (result, verification)
                for key, value in provenance.items()
            ):
                _fail("U005 result or verification lacks exact dual-source provenance")
            successor_receipt = {
                "schema": SUCCESSOR_RECEIPT_SCHEMA_V1,
                **provenance,
                "u002_training_protocol_id": u002["protocol_id"],
                "u004_failed_postprocess_status_retained": True,
                "u004_evidence_reexecuted": False,
                "new_training_execution_ids": [],
                "new_evidence_execution_ids": [],
                "new_tape_roots": [],
                "existing_u004_evidence_transition_replay": True,
                "frozen_analysis_contract_changed": False,
                "independent_verification_schema_is_unchanged_u004_numeric_replay": True,
                "independent_verification_artifact_owned_by_u005_runtime": True,
                "analysis_output_filenames": list(ANALYSIS_OUTPUT_FILENAMES_V1),
                "PROVISIONAL_DESIGN_SIGNAL_GATE": result[
                    "PROVISIONAL_DESIGN_SIGNAL_GATE"
                ],
            }
            write_exclusive_bytes_v1(
                analysis_root / "analysis-successor-receipt.json",
                canonical_json_bytes(successor_receipt),
            )
            status.emit(
                {
                    "event": "ANALYSIS_VERIFICATION_COMPLETED_RETENTION_READY",
                    "analysis_output_file_count": 9,
                    "PROVISIONAL_DESIGN_SIGNAL_GATE": result[
                        "PROVISIONAL_DESIGN_SIGNAL_GATE"
                    ],
                }
            )
        except Exception as error:
            status.emit(
                {
                    "event": "ANALYSIS_SUCCESSOR_FAILED",
                    "failure_kind": type(error).__name__,
                    "failure_message": str(error),
                }
            )
            raise
    retention_entries.extend(
        [
            (
                paths["u004_failed_postprocess_status"],
                "u004_failed_postprocess_status",
                PROVENANCE_U004_FAILURE_V1,
                Path("predecessor-u004/failure/postprocess-status.jsonl"),
            ),
            (
                paths["u005_protocol"],
                "u005_protocol",
                PROVENANCE_U005_AUTHORITY_V1,
                Path("successor-u005/authority/protocol.json"),
            ),
            (
                paths["u005_manifest"],
                "u005_manifest",
                PROVENANCE_U005_AUTHORITY_V1,
                Path("successor-u005/authority/launch-manifest.json"),
            ),
            (
                paths["u005_authority_scan_receipt"],
                "u005_authority_scan_receipt",
                PROVENANCE_U005_AUTHORITY_V1,
                Path("successor-u005/authority/authority-scan-receipt.json"),
            ),
        ]
    )
    retention_entries.extend(_analysis_entries(analysis_root))
    retention_entries.append(
        (
            status_path,
            "u005_postprocess_status",
            PROVENANCE_U005_STATUS_V1,
            Path("successor-u005/status/analysis-postprocess.jsonl"),
        )
    )
    inventory = _copy_retained(
        entries=retention_entries,
        retained_root=retained_root,
        u002=u002,
        u004=u004,
        u005=u005,
    )
    result = _read_object(analysis_root / "pilot-result.json", "pilot result")
    return {
        "success": True,
        "u002_training_protocol_id": u002["protocol_id"],
        "u004_evidence_protocol_id": u004["protocol_id"],
        "u005_analysis_protocol_id": u005["protocol_id"],
        "analysis_execution_id": u005["analysis_execution_id"],
        "analysis_root": str(analysis_root),
        "status_path": str(status_path),
        "retained_root": str(retained_root),
        "retained_artifact_count_excluding_inventory": inventory[
            "retained_artifact_count_excluding_inventory"
        ],
        "physical_file_count_including_inventory": inventory[
            "physical_file_count_including_inventory"
        ],
        "PROVISIONAL_DESIGN_SIGNAL_GATE": result[
            "PROVISIONAL_DESIGN_SIGNAL_GATE"
        ],
        "new_evidence_execution_id_count": 0,
        "new_tape_root_count": 0,
    }


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    for name in (
        "u002_protocol",
        "u002_manifest",
        "u004_protocol",
        "u004_manifest",
        "u004_history_scan_receipt",
        "u004_gather_receipt",
        "u004_failed_postprocess_status",
        "u005_protocol",
        "u005_manifest",
        "u005_authority_scan_receipt",
    ):
        parser.add_argument(f"--{name.replace('_', '-')}", type=Path, required=True)
    parser.add_argument("--analysis-device", default="cuda:0")
    parser.add_argument("--verifier-device", default="cuda:0")
    return parser.parse_args()


def main() -> int:
    try:
        summary = _run(_arguments())
    except (
        LearnedResourceForecastPostprocessU005Error,
        LearnedResourceForecastAnalysisSuccessorProtocolV1Error,
        ScienceExecutionIOV1Error,
        ValueError,
    ) as error:
        raise SystemExit(str(error)) from error
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
