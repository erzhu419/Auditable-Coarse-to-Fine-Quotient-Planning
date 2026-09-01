from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

from acfqp.phase3e_ids import canonical_json_bytes
from acfqp.science.learned_resource_forecast_protocol_v1 import (
    build_ratified_learned_resource_forecast_protocol_v1,
)


REPOSITORY = Path(__file__).resolve().parents[1]
SCANNER = REPOSITORY / "scripts/scan_learned_resource_forecast_history_u001.py"
PREPARE = REPOSITORY / "scripts/prepare_learned_resource_forecast_campaign_u001.py"
SOURCE_COMMIT = "6" * 40


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _bind_fixed_output_paths(module, root: Path) -> None:
    module.FIXED_LAUNCH_ROOT = root
    module.FIXED_RESULTS_ROOT = root.parent / "results"
    module.FIXED_STATUS_ROOT = root.parent / "status"
    module.FIXED_LOG_ROOT = root.parent / "logs"
    module.FIXED_ANALYSIS_ROOT = root.parent / "analysis"
    module.FIXED_RETAINED_ROOT = root.parent / "retained"
    module.FIXED_PROTOCOL_PATH = root / "protocol.json"
    module.FIXED_MANIFEST_PATH = root / "launch-manifest.json"
    module.FIXED_HISTORY_SCAN_RECEIPT_PATH = root / "history-scan-receipt.json"
    module.FIXED_GATHER_TRANSPORT_MARKER_PATH = root / "gather-transport-marker.json"
    module.FIXED_GATHER_RECEIPT_PATH = root / "gather-receipt.json"
    module.FIXED_TRAINING_DISPATCH_STATUS_PATH = root / "training-dispatch.jsonl"
    module.FIXED_EVIDENCE_DISPATCH_STATUS_PATH = root / "evidence-dispatch.jsonl"
    module.FIXED_POSTPROCESS_STATUS_PATH = root / "postprocess-status.jsonl"


def _fixture(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    scanner = _load(SCANNER, "learned_resource_history_scan_subject")
    prepare = _load(PREPARE, "learned_resource_history_scan_prepare")
    launch_root = tmp_path / "launch"
    scan_root = tmp_path / "scan-root"
    scan_root.mkdir()
    _bind_fixed_output_paths(prepare, launch_root)
    protocol = build_ratified_learned_resource_forecast_protocol_v1(SOURCE_COMMIT)
    manifest = prepare.build_launch_manifest_v1(protocol)
    launch_root.mkdir()
    protocol_path = launch_root / "protocol.json"
    manifest_path = launch_root / "launch-manifest.json"
    protocol_path.write_bytes(canonical_json_bytes(protocol))
    manifest_path.write_bytes(canonical_json_bytes(manifest))
    monkeypatch.setattr(scanner, "DEFAULT_SCAN_ROOT", scan_root)
    monkeypatch.setattr(scanner, "_load_prepare_module", lambda: prepare)
    monkeypatch.setattr(
        scanner, "bound_clean_source_commit_v1", lambda _repository: SOURCE_COMMIT
    )
    return scanner, protocol, manifest, protocol_path, manifest_path, scan_root


def test_three_host_zero_hit_receipt_is_written_once_and_validates(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    scanner, protocol, manifest, protocol_path, manifest_path, scan_root = _fixture(
        tmp_path, monkeypatch
    )
    expected_hostname = {
        worker["host_alias"]: worker["expected_hostname"]
        for worker in manifest["workers"]
    }

    def host_scanner(host_alias: str, _request: dict) -> dict:
        return {
            "actual_hostname": expected_hostname[host_alias],
            "scanned_path_count": 123,
            "match_count": 0,
            "matches": [],
        }

    output = Path(manifest["fixed_paths"]["history_scan_receipt"])
    receipt = scanner._scan(
        protocol_path=protocol_path,
        manifest_path=manifest_path,
        output=output,
        scan_root=scan_root,
        scanner=host_scanner,
    )

    assert receipt["no_prior_identity_hits"] is True
    assert receipt["total_match_count"] == 0
    assert len(receipt["execution_ids"]) == 576
    assert len(receipt["seeds"]) == 48
    assert len(receipt["tape_roots"]) == 5
    assert receipt["bare_seed_global_match_is_execution_identity"] is False
    assert receipt["excluded_roots"] == [
        manifest["fixed_paths"]["source_checkout"],
        manifest["fixed_paths"]["launch_root"],
    ]
    assert json.loads(output.read_text(encoding="utf-8")) == receipt
    assert scanner.validate_history_scan_receipt_v1(
        receipt, protocol, manifest
    ) == receipt
    with pytest.raises(Exception, match="File exists|already exists"):
        scanner._scan(
            protocol_path=protocol_path,
            manifest_path=manifest_path,
            output=output,
            scan_root=scan_root,
            scanner=host_scanner,
        )


def test_single_rg_scan_excludes_only_source_and_launch_and_finds_old_identity(
    tmp_path: Path,
) -> None:
    scanner = _load(SCANNER, "learned_resource_history_rg_subject")
    scan_root = tmp_path / "mine_code"
    source = scan_root / "current-source"
    launch = scan_root / "current-launch"
    old = scan_root / "old-campaign"
    source.mkdir(parents=True)
    launch.mkdir()
    old.mkdir()
    pilot = "pilot-execution-fixture"
    execution_id = f"{pilot}:policy-training:RAW:seed:830101"
    tape_root = "acfqp-u001-fixture-tape-root"
    (source / "ignored.json").write_text(execution_id, encoding="utf-8")
    (launch / "ignored.json").write_text(execution_id, encoding="utf-8")
    (old / "evidence.json").write_text(
        f"{execution_id}\n{tape_root}\n830101\n", encoding="utf-8"
    )

    row = scanner._scan_local_host(
        {
            "scan_root": str(scan_root),
            "excluded_roots": [str(source), str(launch)],
            "pilot_execution_identity": pilot,
            "execution_ids": [execution_id],
            "seeds": [830101],
            "tape_roots": [tape_root],
            "campaign_artifact_paths": [],
        }
    )

    assert row["match_count"] == 3
    assert {match["identity_kind"] for match in row["matches"]} == {
        "pilot_execution_identity",
        "execution_id",
        "frozen_tape_root",
    }
    assert {match["path"] for match in row["matches"]} == {
        str(old / "evidence.json")
    }
