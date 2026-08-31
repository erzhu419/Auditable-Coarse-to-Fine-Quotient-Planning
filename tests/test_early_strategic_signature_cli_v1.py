from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

from acfqp.science import early_strategic_signature_protocol_v1 as protocol_subject
from acfqp.science.early_strategic_signature_evaluator_v1 import (
    WORKER_EVIDENCE_SCHEMA_V1,
)
from acfqp.science.latent_resource_hybrid_confirmatory_protocol_v2 import (
    HYBRID_CONFIRMATORY_ARMS_V2,
    HYBRID_CONFIRMATORY_TRAINING_SEEDS_V2,
    build_ratified_hybrid_confirmatory_protocol_v2,
    registered_hybrid_confirmatory_device_v2,
)


REPOSITORY = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPOSITORY / "scripts/run_early_strategic_signature_2048_pilot_v1.py"
PILOT_SOURCE_COMMIT = "1" * 40


def _load_script():
    spec = importlib.util.spec_from_file_location("early_signature_cli", SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise AssertionError("cannot load early-signature CLI")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _parent_documents() -> tuple[dict, dict]:
    protocol = build_ratified_hybrid_confirmatory_protocol_v2(
        protocol_subject.PARENT_U005_SOURCE_COMMIT_V1
    )
    jobs = []
    for arm in HYBRID_CONFIRMATORY_ARMS_V2:
        for seed in HYBRID_CONFIRMATORY_TRAINING_SEEDS_V2:
            jobs.append(
                {
                    "job_ordinal": len(jobs),
                    "arm": arm,
                    "seed": seed,
                    "execution_id": f"u005:{arm}:{seed}",
                    "worker": (
                        seed - HYBRID_CONFIRMATORY_TRAINING_SEEDS_V2[0]
                    )
                    % 2,
                    "device": registered_hybrid_confirmatory_device_v2(seed),
                }
            )
    return protocol, {
        "schema": protocol_subject.PARENT_MANIFEST_SCHEMA_V1,
        "protocol_id": protocol["protocol_id"],
        "source_commit": protocol["source_commit"],
        "job_count": 72,
        "worker_count": 2,
        "jobs": jobs,
    }


def _write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def test_launch_manifest_closes_two_fixed_twelve_policy_workers() -> None:
    module = _load_script()
    parent_protocol, parent_manifest = _parent_documents()
    protocol = protocol_subject.build_pilot_protocol_v1(
        parent_protocol, parent_manifest, PILOT_SOURCE_COMMIT
    )

    manifest = module._launch_manifest(protocol)

    assert manifest["protocol_id"] == protocol["protocol_id"]
    assert manifest["source_commit"] == PILOT_SOURCE_COMMIT
    assert manifest["worker_count"] == 2
    assert [row["policy_count"] for row in manifest["workers"]] == [12, 12]
    assert {
        seed
        for row in manifest["workers"]
        for seed in row["policy_seeds"]
    } == set(HYBRID_CONFIRMATORY_TRAINING_SEEDS_V2)


def test_worker_document_matches_evaluator_interface(tmp_path: Path, monkeypatch) -> None:
    module = _load_script()
    parent_protocol, parent_manifest = _parent_documents()
    protocol = protocol_subject.build_pilot_protocol_v1(
        parent_protocol, parent_manifest, PILOT_SOURCE_COMMIT
    )
    parent_root = tmp_path / "parent"
    _write_json(parent_root / "protocol.json", parent_protocol)
    _write_json(parent_root / "manifest.json", parent_manifest)
    for candidate in protocol["candidate_models"]:
        model = parent_root / "artifacts" / candidate["model_filename"]
        model.parent.mkdir(parents=True, exist_ok=True)
        model.touch()
    protocol_path = tmp_path / "pilot-protocol.json"
    _write_json(protocol_path, protocol)
    output = tmp_path / "worker-0.json"

    monkeypatch.setattr(
        module, "bound_clean_source_commit_v1", lambda _repository: PILOT_SOURCE_COMMIT
    )
    monkeypatch.setattr(
        module,
        "load_evidence_bound_hybrid_confirmatory_matrix_v2",
        lambda **_kwargs: [None] * 72,
    )
    monkeypatch.setattr(module, "load_candidate_policy_v1", lambda *_args: object())
    monkeypatch.setattr(
        module,
        "collect_policy_evidence_v1",
        lambda *_args, **_kwargs: {"collector_fixture": True},
    )
    monkeypatch.setattr(
        module,
        "_runtime_context",
        lambda device: {"device": device, "runtime_fixture": True},
    )

    summary = module._worker(
        SimpleNamespace(
            protocol=protocol_path,
            parent_root=parent_root,
            output=output,
            worker=0,
            device="cuda:0",
        )
    )
    document = json.loads(output.read_text(encoding="utf-8"))

    assert summary["policy_count"] == 12
    assert document["schema"] == WORKER_EVIDENCE_SCHEMA_V1
    assert document["pilot_execution_identity"] == protocol[
        "pilot_execution_identity"
    ]
    assert document["execution_id"].endswith(":worker:0")
    assert document["policy_count"] == len(document["policy_evidence"]) == 12
    assert all("collector" in row and "evidence" not in row for row in document[
        "policy_evidence"
    ])
    assert document["scientific_success_claimed"] is False


def test_evaluate_summary_reports_the_frozen_signal_key(
    tmp_path: Path, monkeypatch
) -> None:
    module = _load_script()
    parent_protocol, parent_manifest = _parent_documents()
    protocol = protocol_subject.build_pilot_protocol_v1(
        parent_protocol, parent_manifest, PILOT_SOURCE_COMMIT
    )
    protocol_path = tmp_path / "pilot-protocol.json"
    _write_json(protocol_path, protocol)
    worker_paths = [tmp_path / f"worker-{index}.json" for index in (0, 1)]
    for index, path in enumerate(worker_paths):
        _write_json(path, {"worker": index})
    output = tmp_path / "pilot-result.json"

    monkeypatch.setattr(
        module, "bound_clean_source_commit_v1", lambda _repository: PILOT_SOURCE_COMMIT
    )
    monkeypatch.setattr(
        module,
        "evaluate_pilot_v1",
        lambda _protocol, _workers: {"PROVISIONAL_DESIGN_SIGNAL_GATE": "PASS"},
    )
    monkeypatch.setattr(
        module,
        "_runtime_context",
        lambda device: {"device": device, "runtime_fixture": True},
    )

    summary = module._evaluate(
        SimpleNamespace(
            protocol=protocol_path,
            worker_document=worker_paths,
            output=output,
        )
    )
    result = json.loads(output.read_text(encoding="utf-8"))

    assert summary["provisional_design_signal"] == "PASS"
    assert result["scientific_success_claimed"] is False
    assert result["evaluation_runtime_context"]["device"] == "cpu"
