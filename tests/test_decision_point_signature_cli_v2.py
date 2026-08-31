from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from acfqp.phase3e_ids import canonical_json_bytes
from acfqp.science import decision_point_signature_protocol_v2 as protocol_subject
from acfqp.science.decision_point_signature_evaluator_v2 import (
    WORKER_EVIDENCE_SCHEMA_V2,
)
from acfqp.science.latent_resource_hybrid_confirmatory_protocol_v2 import (
    HYBRID_CONFIRMATORY_ARMS_V2,
    HYBRID_CONFIRMATORY_TRAINING_SEEDS_V2,
    build_ratified_hybrid_confirmatory_protocol_v2,
    registered_hybrid_confirmatory_device_v2,
)


REPOSITORY = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPOSITORY / "scripts/run_decision_point_signature_2048_pilot_v2.py"
SOURCE_COMMIT = "4" * 40


def _load_script():
    spec = importlib.util.spec_from_file_location("decision_point_cli", SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise AssertionError("cannot load decision-point signature CLI")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _parent_documents() -> tuple[dict, dict]:
    parent = build_ratified_hybrid_confirmatory_protocol_v2(
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
    return parent, {
        "schema": (
            "acfqp.science.latent_resource_hybrid_confirmatory_launch_manifest.v2"
        ),
        "protocol_id": parent["protocol_id"],
        "source_commit": parent["source_commit"],
        "job_count": 72,
        "worker_count": 2,
        "jobs": jobs,
    }


def _prior_result() -> dict:
    labels = []
    for index, seed in enumerate(HYBRID_CONFIRMATORY_TRAINING_SEEDS_V2):
        labels.append(
            {
                "seed": seed,
                "mean_label_score": float(1_000 + index),
                "label": (
                    "NOVICE"
                    if index < 8
                    else "EXPERT"
                    if index >= 16
                    else "EXCLUDED_MIDDLE"
                ),
            }
        )
    return {
        "schema": protocol_subject.PRIOR_RESULT_SCHEMA_V2,
        "protocol_id": protocol_subject.PRIOR_PROTOCOL_ID_V2,
        "source_commit": protocol_subject.PRIOR_SOURCE_COMMIT_V2,
        "pilot_execution_identity": protocol_subject.PRIOR_EXECUTION_IDENTITY_V2,
        "PROVISIONAL_DESIGN_SIGNAL_GATE": "FAIL",
        "provisional_design_signal": "FAIL",
        "scientific_success": False,
        "scientific_success_claimed": False,
        "official_execution_allowed": False,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "SCALAR_CALIBRATION_GATE": "NOT_RUN",
        "BREAK_EVEN_GATE": "NOT_RUN",
        "OFFICIAL_EXECUTION_GATE": "NOT_RUN",
        "policy_labels": labels,
    }


@pytest.fixture(scope="module")
def protocol() -> dict:
    parent, manifest = _parent_documents()
    return protocol_subject.build_decision_point_protocol_v2(
        parent, manifest, _prior_result(), SOURCE_COMMIT
    )


def _write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def test_launch_manifest_closes_two_fixed_twelve_policy_workers(
    protocol: dict,
) -> None:
    module = _load_script()
    manifest = module._launch_manifest(protocol)

    assert manifest["protocol_id"] == protocol["protocol_id"]
    assert manifest["source_commit"] == SOURCE_COMMIT
    assert manifest["worker_count"] == 2
    assert [row["policy_count"] for row in manifest["workers"]] == [12, 12]
    assert {
        seed for row in manifest["workers"] for seed in row["policy_seeds"]
    } == set(HYBRID_CONFIRMATORY_TRAINING_SEEDS_V2)


def test_runtime_context_preserves_exact_version_types() -> None:
    module = _load_script()
    context = module._runtime_context("cpu")

    assert type(context["torch_version"]) is str
    assert (
        context["torch_cuda_runtime_version"] is None
        or type(context["torch_cuda_runtime_version"]) is str
    )
    assert (
        context["torch_cudnn_version"] is None
        or type(context["torch_cudnn_version"]) is int
    )
    canonical_json_bytes(context)


def test_worker_document_matches_evaluator_schema_without_real_collection(
    protocol: dict, tmp_path: Path, monkeypatch, capsys
) -> None:
    module = _load_script()
    parent_root = tmp_path / "parent"
    for candidate in protocol["candidate_models"]:
        model = parent_root / "artifacts" / candidate["model_filename"]
        model.parent.mkdir(parents=True, exist_ok=True)
        model.touch()
    protocol_path = tmp_path / "protocol.json"
    prior_result_path = tmp_path / "prior-result.json"
    output = tmp_path / "worker-0.json"
    _write_json(protocol_path, protocol)
    _write_json(prior_result_path, _prior_result())
    parent_binding_calls = []

    monkeypatch.setattr(
        module, "bound_clean_source_commit_v1", lambda _repository: SOURCE_COMMIT
    )
    monkeypatch.setattr(
        module,
        "_validate_parent_binding",
        lambda **kwargs: parent_binding_calls.append(kwargs),
    )
    monkeypatch.setattr(module, "load_candidate_policy_v2", lambda *_args: object())
    monkeypatch.setattr(
        module,
        "collect_policy_decision_evidence_v2",
        lambda *_args, **_kwargs: {"collector_fixture": True},
    )
    monkeypatch.setattr(
        module,
        "_runtime_context",
        lambda device: {
            "device": device,
            "torch_version": "fixture",
            "runtime_fixture": True,
        },
    )
    import torch

    monkeypatch.setattr(torch.cuda, "empty_cache", lambda: None)

    summary = module._worker(
        SimpleNamespace(
            protocol=protocol_path,
            parent_root=parent_root,
            prior_result=prior_result_path,
            output=output,
            worker=0,
            device="cuda:0",
        )
    )
    document = json.loads(output.read_text(encoding="utf-8"))
    events = [json.loads(line) for line in capsys.readouterr().out.splitlines()]

    assert len(parent_binding_calls) == 1
    assert summary["policy_count"] == 12
    assert document["schema"] == WORKER_EVIDENCE_SCHEMA_V2
    assert document["pilot_execution_identity"] == protocol[
        "pilot_execution_identity"
    ]
    assert document["execution_id"].endswith(":worker:0")
    assert document["policy_count"] == len(document["policy_evidence"]) == 12
    assert all("collector" in row for row in document["policy_evidence"])
    assert document["scientific_success_claimed"] is False
    assert events[0]["event"] == "WORKER_STARTED"
    assert [event["completed_policy_count"] for event in events[1:]] == list(
        range(1, 13)
    )


def test_evaluate_writes_one_result_and_main_prints_one_summary(
    protocol: dict, tmp_path: Path, monkeypatch, capsys
) -> None:
    module = _load_script()
    protocol_path = tmp_path / "protocol.json"
    worker_paths = [tmp_path / f"worker-{index}.json" for index in (0, 1)]
    output = tmp_path / "pilot-result.json"
    _write_json(protocol_path, protocol)
    for index, path in enumerate(worker_paths):
        _write_json(path, {"worker": index})
    monkeypatch.setattr(
        module, "bound_clean_source_commit_v1", lambda _repository: SOURCE_COMMIT
    )
    monkeypatch.setattr(
        module,
        "evaluate_decision_point_pilot_v2",
        lambda _protocol, _workers: {
            "PROVISIONAL_DESIGN_SIGNAL_GATE": "PASS",
            "scientific_success_claimed": False,
        },
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
    assert capsys.readouterr().out == ""

    monkeypatch.setattr(
        module,
        "_arguments",
        lambda: SimpleNamespace(operation="evaluate"),
    )
    monkeypatch.setattr(module, "_evaluate", lambda _args: summary)
    assert module.main() == 0
    lines = capsys.readouterr().out.splitlines()
    assert len(lines) == 1
    assert json.loads(lines[0]) == summary
