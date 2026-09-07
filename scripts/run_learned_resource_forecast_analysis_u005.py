#!/usr/bin/env python3
"""Run frozen U004 measurement analysis under fresh U005 runtime authority."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
import importlib.util
import json
from pathlib import Path
import sys
from typing import Any, NoReturn

from acfqp.science.execution_io_v1 import (
    ScienceExecutionIOV1Error,
    bound_clean_source_commit_v1,
)
from acfqp.science.learned_resource_forecast_analysis_successor_protocol_v1 import (
    LearnedResourceForecastAnalysisSuccessorProtocolV1Error,
    U004_PROTOCOL_ID_V1,
    U004_SOURCE_COMMIT_V1,
    validate_ratified_analysis_successor_protocol_v1,
)


REPOSITORY = Path(__file__).resolve().parents[1]


class LearnedResourceForecastAnalysisU005Error(RuntimeError):
    """The U005 runtime or either read-only predecessor authority is invalid."""


def _fail(message: str) -> NoReturn:
    raise LearnedResourceForecastAnalysisU005Error(message)


def _load_script(module_name: str, filename: str) -> Any:
    path = REPOSITORY / "scripts" / filename
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        _fail(f"cannot load analysis-successor dependency: {filename}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_U004 = _load_script(
    "acfqp_u004_analysis_for_u005",
    "run_learned_resource_forecast_analysis_u004.py",
)
_U005_PREPARE = _load_script(
    "acfqp_u005_prepare_for_u005_analysis",
    "prepare_learned_resource_forecast_analysis_successor_u005.py",
)


def _read_json(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise LearnedResourceForecastAnalysisU005Error(
            f"cannot read {label}: {path}"
        ) from error
    if type(value) is not dict:
        _fail(f"{label} must contain one JSON object")
    return value


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="operation", required=True)

    def authority(command: argparse.ArgumentParser) -> None:
        command.add_argument(
            "--u002-protocol", dest="predecessor_protocol", type=Path, required=True
        )
        command.add_argument(
            "--u002-manifest", dest="predecessor_manifest", type=Path, required=True
        )
        command.add_argument("--u004-protocol", dest="protocol", type=Path, required=True)
        command.add_argument("--u004-manifest", dest="manifest", type=Path, required=True)
        command.add_argument("--u005-protocol", type=Path, required=True)
        command.add_argument("--u005-manifest", type=Path, required=True)

    fit = commands.add_parser("fit-encoders")
    authority(fit)
    fit.add_argument("--trajectory-dir", type=Path, action="append", required=True)
    fit.add_argument("--output-dir", type=Path, required=True)
    fit.add_argument("--device", default="cuda:0")

    encode = commands.add_parser("encode-probes")
    authority(encode)
    encode.add_argument("--probe-dir", type=Path, action="append", required=True)
    encode.add_argument("--aligned-encoder", type=Path, required=True)
    encode.add_argument("--shuffled-encoder", type=Path, required=True)
    encode.add_argument("--output-dir", type=Path, required=True)
    encode.add_argument("--device", default="cuda:0")

    evaluate = commands.add_parser("evaluate")
    authority(evaluate)
    evaluate.add_argument(
        "--predecessor-status-dir", type=Path, action="append", required=True
    )
    evaluate.add_argument("--status-dir", type=Path, action="append", required=True)
    evaluate.add_argument(
        "--predecessor-training-result-dir",
        type=Path,
        action="append",
        required=True,
    )
    evaluate.add_argument(
        "--evidence-dir",
        dest="worker_result_dir",
        type=Path,
        action="append",
        required=True,
    )
    evaluate.add_argument("--matrix", type=Path, required=True)
    evaluate.add_argument("--matrix-metadata", type=Path, required=True)
    evaluate.add_argument("--encoder-receipt-dir", type=Path, required=True)
    evaluate.add_argument("--label-dir", type=Path, action="append", required=True)
    evaluate.add_argument("--output", type=Path, required=True)
    evaluate.add_argument("--device", default="cuda:0")
    return parser


def _arguments(argv: Sequence[str] | None = None) -> argparse.Namespace:
    return _build_parser().parse_args(argv)


def _validate_u005_runtime(args: argparse.Namespace) -> dict[str, Any]:
    protocol = validate_ratified_analysis_successor_protocol_v1(
        _read_json(args.u005_protocol, "ratified U005 protocol")
    )
    manifest = _read_json(args.u005_manifest, "U005 launch manifest")
    if manifest != _U005_PREPARE.build_launch_manifest_v1(protocol):
        _fail("U005 manifest differs from its frozen builder output")
    runtime_commit = bound_clean_source_commit_v1(REPOSITORY)
    fixed = manifest["fixed_paths"]
    if (
        runtime_commit != protocol["source_commit"]
        or REPOSITORY.resolve() != Path(fixed["source_checkout"]).resolve()
        or args.u005_protocol.resolve() != Path(fixed["protocol"]).resolve()
        or args.u005_manifest.resolve() != Path(fixed["manifest"]).resolve()
        or protocol["predecessor_evidence_authority"]["protocol_id"]
        != U004_PROTOCOL_ID_V1
        or protocol["predecessor_evidence_authority"]["source_commit"]
        != U004_SOURCE_COMMIT_V1
        or protocol["execution_contract"]["new_evidence_execution_ids"] != []
        or protocol["execution_contract"]["new_tape_roots"] != []
    ):
        _fail("U005 clean runtime source, paths, or analysis-only boundary changed")
    return protocol


def _run(args: argparse.Namespace) -> dict[str, Any]:
    u005 = _validate_u005_runtime(args)
    _predecessor, u004 = _U004._load_protocols(args)  # noqa: SLF001
    if (
        u004["protocol_id"] != U004_PROTOCOL_ID_V1
        or u004["source_commit"] != U004_SOURCE_COMMIT_V1
        or u005["frozen_analysis_contract"]
        != {key: u004[key] for key in u005["frozen_analysis_contract"]}
    ):
        _fail("U005 did not preserve the exact U004 evidence and analysis contract")
    args.analysis_runtime_protocol_id = u005["protocol_id"]
    args.analysis_runtime_source_commit = u005["source_commit"]
    args.analysis_runtime_execution_id = u005["analysis_execution_id"]
    summary = _U004._run(args)  # noqa: SLF001
    return dict(summary) | {
        "analysis_successor_protocol_id": u005["protocol_id"],
        "analysis_execution_id": u005["analysis_execution_id"],
        "analysis_runtime_source_commit": u005["source_commit"],
        "evidence_measurement_protocol_id": u004["protocol_id"],
        "evidence_measurement_source_commit": u004["source_commit"],
        "u004_evidence_reexecuted": False,
        "new_evidence_execution_id_count": 0,
        "new_tape_root_count": 0,
    }


def main(argv: Sequence[str] | None = None) -> int:
    try:
        summary = _run(_arguments(argv))
    except (
        LearnedResourceForecastAnalysisU005Error,
        LearnedResourceForecastAnalysisSuccessorProtocolV1Error,
        ScienceExecutionIOV1Error,
        ValueError,
    ) as error:
        raise SystemExit(str(error)) from error
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
