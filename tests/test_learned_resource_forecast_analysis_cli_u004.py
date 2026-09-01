from __future__ import annotations

from copy import deepcopy
import importlib.util
import json
from pathlib import Path

import pytest

from acfqp.science.learned_resource_forecast_evidence_successor_protocol_v1 import (
    U002_EXECUTION_IDENTITY_V1,
    U002_SOURCE_COMMIT_V1,
    build_ratified_learned_resource_forecast_evidence_successor_protocol_v1,
)
from acfqp.science.learned_resource_forecast_protocol_v1 import (
    build_ratified_learned_resource_forecast_protocol_v1,
)


REPOSITORY = Path(__file__).resolve().parents[1]
SUCCESSOR_COMMIT = "9" * 40


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
        "acfqp_u004_analysis_test_subject",
        "run_learned_resource_forecast_analysis_u004.py",
    )


@pytest.fixture(scope="module")
def verifier():
    return _load_script(
        "acfqp_u004_verifier_test_subject",
        "verify_learned_resource_forecast_analysis_u004.py",
    )


@pytest.fixture(scope="module")
def authority_bundle(analysis):
    predecessor_protocol = build_ratified_learned_resource_forecast_protocol_v1(
        U002_SOURCE_COMMIT_V1
    )
    successor_protocol = (
        build_ratified_learned_resource_forecast_evidence_successor_protocol_v1(
            SUCCESSOR_COMMIT
        )
    )
    predecessor_manifest = analysis._U002_PREPARE.build_launch_manifest_v1(  # noqa: SLF001
        predecessor_protocol
    )
    successor_manifest = analysis._U004_PREPARE.build_launch_manifest_v1(  # noqa: SLF001
        successor_protocol
    )
    return (
        predecessor_protocol,
        successor_protocol,
        predecessor_manifest,
        successor_manifest,
    )


def test_analysis_parser_requires_both_protocol_authorities(analysis) -> None:
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
                "u004-protocol.json",
                "--manifest",
                "u004-manifest.json",
                "--trajectory-dir",
                "trajectories",
                "--output-dir",
                "encoders",
            ]
        )


def test_exact_dual_manifest_closes_and_excludes_u002_evidence(
    analysis, authority_bundle
) -> None:
    predecessor, successor, old_manifest, new_manifest = authority_bundle
    replayed = analysis._validate_dual_manifests(  # noqa: SLF001
        old_manifest,
        new_manifest,
        predecessor_protocol=predecessor,
        successor_protocol=successor,
    )
    assert len(replayed["training_jobs"]) == 144
    assert len(replayed["player_jobs"]) == 432
    assert new_manifest["phase_roster"] == ["evidence"]
    assert all(
        not job["execution_id"].startswith(
            f"{U002_EXECUTION_IDENTITY_V1}:player-evidence:"
        )
        for job in replayed["player_jobs"].values()
    )


def test_tampered_predecessor_manifest_is_rejected(
    analysis, authority_bundle
) -> None:
    predecessor, successor, old_manifest, new_manifest = authority_bundle
    tampered = deepcopy(old_manifest)
    tampered["workers"][0]["policy_training_jobs"][0]["seed"] += 1
    with pytest.raises(
        analysis.LearnedResourceForecastAnalysisU004Error,
        match="predecessor manifest",
    ):
        analysis._validate_dual_manifests(  # noqa: SLF001
            tampered,
            new_manifest,
            predecessor_protocol=predecessor,
            successor_protocol=successor,
        )


def _ownership_document(
    predecessor: dict, successor: dict, job: dict
) -> dict:
    return {
        "protocol_id": successor["protocol_id"],
        "source_commit": successor["source_commit"],
        "pilot_execution_identity": successor["pilot_execution_identity"],
        "player_identity": {
            "player_key": job["player_key"],
            "base_training_seed": job["seed"],
            "generator_arm": job["arm"],
            "checkpoint_environment_interactions": job["checkpoint"],
            "split": job["split"],
            "generator_arm_checkpoint_seed_are_not_classifier_inputs": True,
        },
        "execution_context": {
            "execution_id": job["execution_id"],
            "source_commit": successor["source_commit"],
            "hostname": job["expected_hostname"],
            "device": job["device"],
        },
        "policy_snapshot": {
            "path": str(
                Path(successor["predecessor_training_authority"]["results_root"])
                / f"worker-{job['worker']}"
                / job["model_filename"]
            ),
            "artifact_kind": "INFERENCE_ONLY_BARE_ONLINE_STATE_DICT",
            "predecessor_protocol_id": predecessor["protocol_id"],
            "predecessor_source_commit": predecessor["source_commit"],
            "predecessor_training_execution_id": job[
                "predecessor_training_execution_id"
            ],
            "predecessor_pilot_execution_identity": predecessor[
                "pilot_execution_identity"
            ],
            "snapshot_is_read_only_predecessor_input": True,
            "snapshot_is_u004_training_artifact": False,
        },
    }


def test_primary_and_independent_ownership_require_parent_snapshot_fields(
    analysis, verifier, authority_bundle
) -> None:
    predecessor, successor, old_manifest, new_manifest = authority_bundle
    primary_manifest = analysis._validate_dual_manifests(  # noqa: SLF001
        old_manifest,
        new_manifest,
        predecessor_protocol=predecessor,
        successor_protocol=successor,
    )
    independent_manifest = verifier._replay_dual_manifest(  # noqa: SLF001
        old_manifest,
        new_manifest,
        predecessor_protocol=predecessor,
        successor_protocol=successor,
    )
    job = next(iter(primary_manifest["player_jobs"].values()))
    independent_job = independent_manifest["players"][job["player_key"]]
    document = _ownership_document(predecessor, successor, job)
    analysis._ownership_validator(predecessor, successor)(  # noqa: SLF001
        document, protocol=successor, job=job
    )
    verifier._ownership_validator(predecessor, successor)(  # noqa: SLF001
        document, protocol=successor, job=independent_job
    )

    tampered = deepcopy(document)
    tampered["policy_snapshot"]["predecessor_training_execution_id"] += ":other"
    with pytest.raises(
        analysis.LearnedResourceForecastAnalysisU004Error,
        match="dual-authority",
    ):
        analysis._ownership_validator(predecessor, successor)(  # noqa: SLF001
            tampered, protocol=successor, job=job
        )
    with pytest.raises(
        verifier.LearnedResourceForecastIndependentVerifierU004Error,
        match="predecessor snapshot",
    ):
        verifier._ownership_validator(predecessor, successor)(  # noqa: SLF001
            tampered, protocol=successor, job=independent_job
        )


def _closed_status_rows(phase: str, worker: int, execution_id: str) -> list[dict]:
    return [
        {"event": "WORKER_STARTED", "phase": phase, "worker": worker},
        {
            "event": "JOB_STARTED",
            "phase": phase,
            "worker": worker,
            "job_ordinal": 0,
            "execution_id": execution_id,
            "preexecution_identity_check_only": False,
        },
        {
            "event": "JOB_COMPLETED",
            "phase": phase,
            "worker": worker,
            "job_ordinal": 0,
            "execution_id": execution_id,
            "completed_job_count": 1,
            "expected_job_count": 1,
        },
        {
            "event": "WORKER_COMPLETED",
            "phase": phase,
            "worker": worker,
            "completed_job_count": 1,
        },
    ]


def test_status_replay_rejects_cross_authority_execution_id(
    analysis, verifier, tmp_path: Path
) -> None:
    path = tmp_path / "worker-0-evidence.jsonl"
    path.write_text(
        "\n".join(json.dumps(row) for row in _closed_status_rows("evidence", 0, "u004:e0"))
        + "\n",
        encoding="utf-8",
    )
    roster = {"phase": "evidence", "worker": 0, "execution_ids": ("u004:e0",)}
    assert analysis._validate_status_stream(  # noqa: SLF001
        (tmp_path,), path.name, roster
    ) == 1
    assert verifier._replay_stream((tmp_path,), path.name, roster) == 1  # noqa: SLF001
    foreign = dict(roster) | {"execution_ids": ("u002:e0",)}
    with pytest.raises(analysis.LearnedResourceForecastAnalysisU004Error):
        analysis._validate_status_stream((tmp_path,), path.name, foreign)  # noqa: SLF001
    with pytest.raises(
        verifier.LearnedResourceForecastIndependentVerifierU004Error
    ):
        verifier._replay_stream((tmp_path,), path.name, foreign)  # noqa: SLF001
