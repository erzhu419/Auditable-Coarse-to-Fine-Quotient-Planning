from __future__ import annotations

import importlib.util
import json
from pathlib import Path

from acfqp.science.learned_resource_forecast_evidence_v1 import (
    expected_player_evidence_execution_id_v1,
)
from acfqp.science.learned_resource_forecast_protocol_v1 import (
    LEARNED_RESOURCE_FORECAST_TEST_SEEDS_V1,
    LEARNED_RESOURCE_FORECAST_TRAIN_SEEDS_V1,
    build_ratified_learned_resource_forecast_protocol_v1,
)


REPOSITORY = Path(__file__).resolve().parents[1]
SCRIPT = REPOSITORY / "scripts/prepare_learned_resource_forecast_campaign_u001.py"
SOURCE_COMMIT = "7" * 40


def _module():
    spec = importlib.util.spec_from_file_location("prepare_lrf_u001", SCRIPT)
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


def test_six_worker_manifest_closes_interleaved_seed_and_identity_rosters() -> None:
    module = _module()
    _bind_fixed_output_paths(module, Path("/tmp/u001-launch-test"))
    protocol = build_ratified_learned_resource_forecast_protocol_v1(SOURCE_COMMIT)
    manifest = module.build_launch_manifest_v1(protocol)

    assert manifest["worker_count"] == 6
    assert manifest["source_checkout"] == str(module.FIXED_SOURCE_CHECKOUT)
    assert manifest["source_pythonpath"] == str(module.FIXED_SOURCE_PYTHONPATH)
    assert manifest["required_runtime"]["source_pythonpath"] == str(
        module.FIXED_SOURCE_PYTHONPATH
    )
    assert manifest["required_runtime"][
        "acfqp_import_must_resolve_inside_source_pythonpath"
    ] is True
    assert manifest["required_runtime"][
        "pythonpath_environment_must_equal_source_pythonpath"
    ] is True
    assert [len(worker["seeds"]) for worker in manifest["workers"]] == [8] * 6
    assert sum(
        len(worker["policy_training_jobs"]) for worker in manifest["workers"]
    ) == 144
    assert sum(
        len(worker["player_evidence_jobs"]) for worker in manifest["workers"]
    ) == 432
    for seed in (*LEARNED_RESOURCE_FORECAST_TRAIN_SEEDS_V1,
                 *LEARNED_RESOURCE_FORECAST_TEST_SEEDS_V1):
        owners = [
            worker["worker"]
            for worker in manifest["workers"]
            if seed in worker["seeds"]
        ]
        assert len(owners) == 1
    assert all(
        worker["train_seed_count"] > 0 and worker["test_seed_count"] > 0
        for worker in manifest["workers"]
    )
    evidence = [
        job
        for worker in manifest["workers"]
        for job in worker["player_evidence_jobs"]
    ]
    assert sum(job["trajectory_array_filename"] is not None for job in evidence) == 288
    assert all(
        (job["trajectory_array_filename"] is not None) == (job["split"] == "TRAIN")
        for job in evidence
    )
    assert all(
        job["execution_id"]
        == expected_player_evidence_execution_id_v1(
            protocol,
            base_seed=job["seed"],
            generator_arm=job["arm"],
            checkpoint=job["checkpoint"],
        )
        for job in evidence
    )


def test_prepare_reexports_the_authoritative_evidence_identity_helper() -> None:
    module = _module()
    _bind_fixed_output_paths(module, Path("/tmp/u001-launch-helper-test"))
    assert (
        module.expected_player_evidence_execution_id_v1
        is expected_player_evidence_execution_id_v1
    )


def test_prepare_exclusively_writes_protocol_and_manifest(
    tmp_path: Path, monkeypatch
) -> None:
    module = _module()
    monkeypatch.setattr(
        module, "bound_clean_source_commit_v1", lambda _repository: SOURCE_COMMIT
    )
    root = tmp_path / "launch"
    _bind_fixed_output_paths(module, root)
    summary = module._prepare(root)
    assert summary["policy_training_jobs"] == 144
    assert sorted(path.name for path in root.iterdir()) == [
        "launch-manifest.json",
        "protocol.json",
    ]
    protocol = json.loads((root / "protocol.json").read_text(encoding="utf-8"))
    manifest = json.loads(
        (root / "launch-manifest.json").read_text(encoding="utf-8")
    )
    assert manifest["protocol_id"] == protocol["protocol_id"]
    assert manifest["source_commit"] == SOURCE_COMMIT
