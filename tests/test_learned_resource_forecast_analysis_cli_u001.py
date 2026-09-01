from __future__ import annotations

from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import socket
import sys

import numpy as np
import pytest

from acfqp.science import learned_resource_forecast_evaluator_v1 as evaluator
from acfqp.science import learned_resource_forecast_evidence_v1 as evidence
from acfqp.science import learned_resource_forecast_protocol_v1 as protocol_v1


REPOSITORY = Path(__file__).resolve().parents[1]
SOURCE_COMMIT = "8" * 40


def _load_script(module_name: str, filename: str):
    spec = importlib.util.spec_from_file_location(
        module_name, REPOSITORY / "scripts" / filename
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def analysis():
    return _load_script(
        "acfqp_u001_analysis_test_subject",
        "run_learned_resource_forecast_analysis_u001.py",
    )


@pytest.fixture(scope="module")
def verifier():
    return _load_script(
        "acfqp_u001_verifier_test_subject",
        "verify_learned_resource_forecast_analysis_u001.py",
    )


@pytest.fixture(scope="module")
def protocol() -> dict:
    return protocol_v1.build_ratified_learned_resource_forecast_protocol_v1(
        SOURCE_COMMIT
    )


def _first_legal(_state, legal_mask):
    return legal_mask.index(True)


def test_analysis_parser_has_three_lane_separated_subcommands(analysis) -> None:
    parser = analysis._build_parser()  # noqa: SLF001
    subparsers = next(
        action
        for action in parser._actions  # noqa: SLF001
        if getattr(action, "choices", None)
    )
    assert set(subparsers.choices) == {
        "fit-encoders",
        "encode-probes",
        "evaluate",
    }
    with pytest.raises(SystemExit):
        analysis._arguments(  # noqa: SLF001
            [
                "fit-encoders",
                "--protocol",
                "protocol.json",
                "--manifest",
                "manifest.json",
                "--trajectory-dir",
                "trajectory",
                "--output-dir",
                "encoders",
                "--label-dir",
                "labels",
            ]
        )


def _probe_fixture(protocol: dict, tmp_path: Path) -> tuple[Path, dict]:
    seed = protocol_v1.LEARNED_RESOURCE_FORECAST_TEST_SEEDS_V1[0]
    arm = protocol_v1.LEARNED_RESOURCE_FORECAST_ARMS_V1[0]
    checkpoint = protocol_v1.LEARNED_RESOURCE_FORECAST_CHECKPOINTS_V1[0]
    key = protocol_v1.player_key_v1(seed, arm, checkpoint)
    execution = evidence.expected_player_evidence_execution_id_v1(
        protocol,
        base_seed=seed,
        generator_arm=arm,
        checkpoint=checkpoint,
    )
    model_name = f"{arm.lower()}-seed-{seed}-checkpoint-{checkpoint}.pt"
    artifacts = evidence._collect_player_evidence_with_selector_v1(  # noqa: SLF001
        protocol=protocol,
        action_selector=_first_legal,
        base_seed=seed,
        generator_arm=arm,
        checkpoint=checkpoint,
        execution_context={
            "execution_id": execution,
            "source_commit": SOURCE_COMMIT,
            "hostname": "fixture-host",
            "device": "cuda:0",
        },
        snapshot_reference=model_name,
        trajectory_episode_count=0,
        label_episode_count=1,
        probe_count=16,
    )
    filename = f"{arm.lower()}-seed-{seed}-checkpoint-{checkpoint}.probe.json"
    document = dict(artifacts.probe_document)
    document["artifact_manifest"] = {
        "lane": "EIGHT_ACTION_NATURAL_OPENING_PROBE",
        "filename": filename,
        "contains_other_lane_content": False,
    }
    path = tmp_path / filename
    path.write_text(json.dumps(document), encoding="utf-8")
    job = {
        "player_key": key,
        "seed": seed,
        "arm": arm,
        "checkpoint": checkpoint,
        "split": "TEST",
        "execution_id": execution,
        "model_filename": model_name,
        "expected_hostname": "fixture-host",
        "device": "cuda:0",
    }
    return path, job


def test_shared_probe_root_is_accepted_and_old_player_suffix_is_rejected(
    analysis, protocol: dict, tmp_path: Path
) -> None:
    path, job = _probe_fixture(protocol, tmp_path)
    traces, root = analysis._probe_traces_from_document(  # noqa: SLF001
        path, protocol=protocol, job=job
    )
    assert len(traces) == 16
    assert root == protocol["probe_tape_root"]

    document = json.loads(path.read_text(encoding="utf-8"))
    document["probe_tape_root"] += f":player:{job['player_key']}"
    path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(
        analysis.LearnedResourceForecastAnalysisCLIError,
        match="lane identity",
    ):
        analysis._probe_traces_from_document(  # noqa: SLF001
            path, protocol=protocol, job=job
        )


def test_probe_transition_tampering_is_rejected(
    analysis, protocol: dict, tmp_path: Path
) -> None:
    path, job = _probe_fixture(protocol, tmp_path)
    document = json.loads(path.read_text(encoding="utf-8"))
    document["probe_rows"][0]["merge_scores"][0] += 1
    path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(
        analysis.LearnedResourceForecastAnalysisCLIError,
        match="exact transition replay",
    ):
        analysis._probe_traces_from_document(  # noqa: SLF001
            path, protocol=protocol, job=job
        )


def _successful_status_rows(phase: str, worker: int, ids: list[str]) -> list[dict]:
    rows = [{"event": "WORKER_STARTED", "phase": phase, "worker": worker}]
    for ordinal, execution in enumerate(ids):
        rows.append(
            {
                "event": "JOB_STARTED",
                "phase": phase,
                "worker": worker,
                "job_ordinal": ordinal,
                "execution_id": execution,
                "preexecution_identity_check_only": False,
            }
        )
        rows.append(
            {
                "event": "JOB_COMPLETED",
                "phase": phase,
                "worker": worker,
                "job_ordinal": ordinal,
                "execution_id": execution,
                "completed_job_count": ordinal + 1,
                "expected_job_count": len(ids),
            }
        )
    rows.append(
        {
            "event": "WORKER_COMPLETED",
            "phase": phase,
            "worker": worker,
            "completed_job_count": len(ids),
        }
    )
    return rows


def test_status_without_terminal_worker_completion_is_rejected(
    analysis, tmp_path: Path
) -> None:
    training = {}
    evidence_rosters = {}
    training_rosters = {}
    for worker in range(6):
        training_ids = [f"training-{worker}-{index}" for index in range(24)]
        evidence_ids = [f"evidence-{worker}-{index}" for index in range(72)]
        training_name = f"worker-{worker}-training.jsonl"
        evidence_name = f"worker-{worker}-evidence.jsonl"
        training_rosters[training_name] = {
            "phase": "training",
            "worker": worker,
            "execution_ids": tuple(training_ids),
        }
        evidence_rosters[evidence_name] = {
            "phase": "evidence",
            "worker": worker,
            "execution_ids": tuple(evidence_ids),
        }
        for name, rows in (
            (training_name, _successful_status_rows("training", worker, training_ids)),
            (evidence_name, _successful_status_rows("evidence", worker, evidence_ids)),
        ):
            (tmp_path / name).write_text(
                "".join(json.dumps(row) + "\n" for row in rows),
                encoding="utf-8",
            )
    manifest = {
        "training_stream_rosters": training_rosters,
        "evidence_stream_rosters": evidence_rosters,
    }
    counts = analysis._status_counts([tmp_path], manifest)  # noqa: SLF001
    assert counts["completed_training_jobs"] == 144
    assert counts["completed_player_evidence_jobs"] == 432

    broken = tmp_path / "worker-0-evidence.jsonl"
    lines = broken.read_text(encoding="utf-8").splitlines()
    broken.write_text("\n".join(lines[:-1]) + "\n", encoding="utf-8")
    with pytest.raises(
        analysis.LearnedResourceForecastAnalysisCLIError,
        match="lifecycle",
    ):
        analysis._status_counts([tmp_path], manifest)  # noqa: SLF001


@pytest.mark.parametrize("missing_name", ["training.json", "checkpoint.pt"])
def test_worker_inventory_rejects_missing_json_or_pt(
    analysis, tmp_path: Path, missing_name: str
) -> None:
    directories = []
    workers = []
    for worker in range(6):
        directory = tmp_path / str(worker)
        directory.mkdir()
        directories.append(directory)
        training_jobs = []
        if worker == 0:
            training_jobs = [
                {
                    "result_filename": "training.json",
                    "checkpoint_filenames": ["checkpoint.pt"],
                }
            ]
            for filename in ("training.json", "checkpoint.pt"):
                if filename != missing_name:
                    (directory / filename).write_bytes(b"fixture")
        workers.append(
            {
                "policy_training_jobs": training_jobs,
                "player_evidence_jobs": [],
            }
        )
    with pytest.raises(
        analysis.LearnedResourceForecastAnalysisCLIError,
        match="missing",
    ):
        analysis._validate_worker_result_inventory(  # noqa: SLF001
            directories, {"document": {"workers": workers}}
        )


def _statistical_fixture() -> tuple[
    list[dict], dict[str, dict[str, np.ndarray]], dict[str, np.ndarray]
]:
    labels = []
    nested = {
        representation: {}
        for representation in protocol_v1.PROBE_REPRESENTATION_ARMS_V1
    }
    arrays = {
        representation: []
        for representation in protocol_v1.PROBE_REPRESENTATION_ARMS_V1
    }
    for seed in protocol_v1.LEARNED_RESOURCE_FORECAST_TRAINING_SEEDS_V1:
        for arm_index, arm in enumerate(
            protocol_v1.LEARNED_RESOURCE_FORECAST_ARMS_V1
        ):
            for checkpoint_index, checkpoint in enumerate(
                protocol_v1.LEARNED_RESOURCE_FORECAST_CHECKPOINTS_V1
            ):
                slot = arm_index * 3 + checkpoint_index
                key = protocol_v1.player_key_v1(seed, arm, checkpoint)
                labels.append(
                    {
                        "base_seed": seed,
                        "generator_arm": arm,
                        "checkpoint": checkpoint,
                        "episode_count": 64,
                        "mean_total_merge_score": float(1_000 * slot),
                    }
                )
                raw = np.zeros((16, 184), dtype=np.float32)
                shuffled = np.zeros((16, 248), dtype=np.float32)
                aligned = np.zeros((16, 248), dtype=np.float32)
                if slot <= 2:
                    aligned[:, -1] = -1.0
                elif slot >= 6:
                    aligned[:, -1] = 1.0
                for representation, matrix in (
                    (protocol_v1.RAW_PREFIX_ARM_V1, raw),
                    (protocol_v1.SHUFFLED_FORECAST_ARM_V1, shuffled),
                    (protocol_v1.ALIGNED_FORECAST_ARM_V1, aligned),
                ):
                    nested[representation][key] = matrix
                    arrays[representation].append(matrix)
    return labels, nested, {
        name: np.asarray(rows, dtype=np.float32)
        for name, rows in arrays.items()
    }


def _complete_counts() -> dict[str, int]:
    return {
        "completed_training_jobs": 144,
        "failed_training_jobs": 0,
        "model_snapshots": 432,
        "trajectory_player_artifacts": 288,
        "complete_trajectory_episodes": 4_608,
        "forecast_encoder_receipts": 2,
        "frozen_encoder_states": 2,
        "completed_player_evidence_jobs": 432,
        "failed_player_evidence_jobs": 0,
        "label_aggregates": 432,
        "exact_eight_action_probe_records": 6_912,
        "missing_identities": 0,
        "duplicate_identities": 0,
        "foreign_identities": 0,
    }


def test_independent_statistics_exactly_match_primary_evaluator(
    verifier, protocol: dict
) -> None:
    labels, nested, arrays = _statistical_fixture()
    expected = evaluator.evaluate_learned_resource_forecast_pilot_v1(
        protocol, labels, nested, _complete_counts()
    )
    observed = verifier._independent_evaluate(  # noqa: SLF001
        protocol, labels, arrays, _complete_counts()
    )
    assert observed == expected

    flat_labels = deepcopy(labels)
    for row in flat_labels:
        row["mean_total_merge_score"] = 0.0
    expected_failure = evaluator.evaluate_learned_resource_forecast_pilot_v1(
        protocol, flat_labels, nested, _complete_counts()
    )
    observed_failure = verifier._independent_evaluate(  # noqa: SLF001
        protocol, flat_labels, arrays, _complete_counts()
    )
    assert observed_failure == expected_failure


def test_tampered_pilot_result_is_rejected(verifier) -> None:
    result = {
        "schema": verifier.EVALUATION_SCHEMA_V1,
        "scientific_success": False,
        "scientific_success_claimed": False,
        "PROVISIONAL_DESIGN_SIGNAL_GATE": "PASS",
    }
    verifier._require_exact_replayed_result(result, deepcopy(result))  # noqa: SLF001
    tampered = deepcopy(result)
    tampered["PROVISIONAL_DESIGN_SIGNAL_GATE"] = "FAIL"
    with pytest.raises(
        verifier.LearnedResourceForecastIndependentVerifierV1Error,
        match="differs",
    ):
        verifier._require_exact_replayed_result(tampered, result)  # noqa: SLF001


def test_runtime_binding_rejects_wrong_acfqp_import_origin(
    analysis, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    import acfqp
    import scipy
    import torch

    source_path = (REPOSITORY / "src").resolve()
    monkeypatch.setenv("PYTHONPATH", str(source_path))
    monkeypatch.setattr(acfqp, "__file__", str(tmp_path / "acfqp" / "__init__.py"))
    manifest = {
        "document": {
            "required_runtime": {
                "python_version": ".".join(
                    str(value) for value in sys.version_info[:3]
                ),
                "python_path": str(Path(sys.executable).resolve()),
                "numpy_version": np.__version__,
                "scipy_version": scipy.__version__,
                "torch_version": str(torch.__version__),
                "torch_cuda_runtime_version": torch.version.cuda,
            },
            "central_analysis": {
                "expected_hostname": socket.gethostname(),
                "device": "cuda:0",
            },
        }
    }
    with pytest.raises(
        analysis.LearnedResourceForecastAnalysisCLIError,
        match="package origin",
    ):
        analysis._validate_analysis_runtime(  # noqa: SLF001
            manifest, requested_device="cuda:0"
        )
