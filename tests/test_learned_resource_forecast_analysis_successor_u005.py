from __future__ import annotations

from copy import deepcopy
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from acfqp.science import learned_resource_forecast_evidence_v1 as evidence
from acfqp.science.learned_resource_forecast_2048_v1 import (
    aligned_forecast_examples_v1,
)
from acfqp.science.learned_resource_forecast_analysis_successor_protocol_v1 import (
    ANALYSIS_EXECUTION_ID_V1,
    ANALYSIS_OUTPUT_FILENAMES_V1,
    EXECUTION_IDENTITY_V1,
    U004_PROTOCOL_ID_V1,
    U004_SOURCE_COMMIT_V1,
    build_ratified_analysis_successor_protocol_v1,
    frozen_analysis_contract_v1,
    u004_evidence_protocol_v1,
    validate_ratified_analysis_successor_protocol_v1,
)
from acfqp.science.learned_resource_forecast_protocol_v1 import (
    LEARNED_RESOURCE_FORECAST_ARMS_V1,
    LEARNED_RESOURCE_FORECAST_TRAIN_SEEDS_V1,
    player_key_v1,
)
from acfqp.science.matched_double_dqn_2048_learned_resource_pilot_v1 import (
    policy_checkpoint_filename_v1,
)


REPOSITORY = Path(__file__).resolve().parents[1]
U005_COMMIT = "a" * 40


def _load_script(module_name: str, filename: str):
    spec = importlib.util.spec_from_file_location(
        module_name, REPOSITORY / "scripts" / filename
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def base_analysis():
    return _load_script(
        "acfqp_u005_base_analysis_test",
        "run_learned_resource_forecast_analysis_u002.py",
    )


@pytest.fixture(scope="module")
def base_verifier():
    return _load_script(
        "acfqp_u005_base_verifier_test",
        "verify_learned_resource_forecast_analysis_u002.py",
    )


@pytest.fixture(scope="module")
def prepare():
    return _load_script(
        "acfqp_u005_prepare_test",
        "prepare_learned_resource_forecast_analysis_successor_u005.py",
    )


@pytest.fixture(scope="module")
def history():
    return _load_script(
        "acfqp_u005_history_test",
        "scan_learned_resource_forecast_analysis_history_u005.py",
    )


@pytest.fixture(scope="module")
def successor_verifier():
    return _load_script(
        "acfqp_u005_successor_verifier_test",
        "verify_learned_resource_forecast_analysis_u005.py",
    )


@pytest.fixture(scope="module")
def postprocess():
    return _load_script(
        "acfqp_u005_postprocess_test",
        "postprocess_retain_learned_resource_forecast_u005.py",
    )


def _first_legal(_state, mask: tuple[bool, bool, bool, bool]) -> int:
    return next(index for index, allowed in enumerate(mask) if allowed)


@pytest.fixture(scope="module")
def production_trajectory_artifacts(tmp_path_factory):
    protocol = u004_evidence_protocol_v1()
    seed = LEARNED_RESOURCE_FORECAST_TRAIN_SEEDS_V1[0]
    arm = LEARNED_RESOURCE_FORECAST_ARMS_V1[0]
    checkpoint = 25_000
    names = evidence.player_evidence_artifact_basenames_v1(
        base_seed=seed, generator_arm=arm, checkpoint=checkpoint
    )
    model_filename = policy_checkpoint_filename_v1(
        arm=arm, seed=seed, checkpoint=checkpoint
    )
    job = {
        "player_key": player_key_v1(seed, arm, checkpoint),
        "seed": seed,
        "arm": arm,
        "checkpoint": checkpoint,
        "split": "TRAIN",
        "execution_id": evidence.expected_player_evidence_execution_id_v1(
            protocol,
            base_seed=seed,
            generator_arm=arm,
            checkpoint=checkpoint,
        ),
        "model_filename": model_filename,
        "expected_hostname": "u005-regression-host",
        "device": "cpu",
    }
    artifacts = evidence._collect_player_evidence_with_selector_v1(
        protocol=protocol,
        action_selector=_first_legal,
        base_seed=seed,
        generator_arm=arm,
        checkpoint=checkpoint,
        execution_context={
            "execution_id": job["execution_id"],
            "source_commit": protocol["source_commit"],
            "hostname": job["expected_hostname"],
            "device": job["device"],
        },
        snapshot_reference=f"/server/models/{model_filename}",
        trajectory_episode_count=16,
        label_episode_count=1,
        probe_count=1,
    )
    assert artifacts.trajectory_document is not None
    document = dict(artifacts.trajectory_document)
    document["artifact_manifest"] = {
        "lane": "SELF_SUPERVISED_TRAJECTORY",
        "metadata_filename": names["trajectory_json"],
        "compressed_array_filename": names["trajectory_npz"],
        "contains_other_lane_content": False,
    }
    root = tmp_path_factory.mktemp("u005-production-trajectory")
    metadata_path = root / names["trajectory_json"]
    array_path = root / names["trajectory_npz"]
    metadata_path.write_text(json.dumps(document, sort_keys=True), encoding="utf-8")
    array_path.write_bytes(
        evidence.forecast_examples_npz_bytes_v1(artifacts.trajectory_examples)
    )
    return protocol, job, metadata_path, array_path, artifacts.trajectory_examples


def test_protocol_preserves_u004_method_and_is_analysis_only(prepare, history) -> None:
    u004 = u004_evidence_protocol_v1()
    u005 = build_ratified_analysis_successor_protocol_v1(U005_COMMIT)
    manifest = prepare.build_launch_manifest_v1(u005)
    assert u004["protocol_id"] == U004_PROTOCOL_ID_V1
    assert u004["source_commit"] == U004_SOURCE_COMMIT_V1
    assert u005["frozen_analysis_contract"] == frozen_analysis_contract_v1()
    assert u005["pilot_execution_identity"] == EXECUTION_IDENTITY_V1
    assert u005["analysis_execution_id"] == ANALYSIS_EXECUTION_ID_V1
    assert u005["execution_contract"]["same_identity_retry_allowed"] is False
    assert u005["execution_contract"]["existing_u004_evidence_transition_replay"] is True
    assert u005["execution_contract"]["new_policy_or_evidence_measurement_executed"] is False
    assert manifest["new_training_execution_ids"] == []
    assert manifest["new_evidence_execution_ids"] == []
    assert manifest["new_tape_roots"] == []
    assert manifest["expected_counts"] == {
        "read_only_u002_training_jobs": 144,
        "read_only_u002_model_snapshots": 432,
        "read_only_u004_evidence_jobs": 432,
        "new_training_jobs": 0,
        "new_evidence_jobs": 0,
        "new_tape_roots": 0,
        "analysis_jobs": 1,
        "analysis_output_files": 9,
    }
    request = history._expected_request(u005, manifest, history.DEFAULT_SCAN_ROOT)
    assert request["excluded_roots"] == [
        manifest["fixed_paths"]["source_checkout"],
        manifest["fixed_paths"]["launch_root"],
    ]
    assert request["execution_ids"] == [
        u005["analysis_execution_id"],
        u005["protocol_id"],
    ]
    assert request["campaign_artifact_paths"] == [
        manifest["fixed_paths"]["analysis_root"],
        manifest["fixed_paths"]["status_root"],
        manifest["fixed_paths"]["retained_root"],
    ]
    assert request["seeds"] == request["tape_roots"] == []


def test_actual_trajectory_construction_reproduces_then_fixes_nameerror(
    base_analysis, production_trajectory_artifacts, monkeypatch
) -> None:
    protocol, job, metadata_path, array_path, expected = production_trajectory_artifacts
    monkeypatch.delattr(base_analysis, "aligned_forecast_examples_v1")
    with pytest.raises(
        NameError, match="name 'aligned_forecast_examples_v1' is not defined"
    ):
        base_analysis._trajectory_examples_from_artifacts(
            metadata_path, array_path, protocol=protocol, job=job
        )
    monkeypatch.setattr(
        base_analysis,
        "aligned_forecast_examples_v1",
        aligned_forecast_examples_v1,
        raising=False,
    )
    actual, tape_root, episode_count = (
        base_analysis._trajectory_examples_from_artifacts(
            metadata_path, array_path, protocol=protocol, job=job
        )
    )
    assert [row.key for row in actual] == [row.key for row in expected]
    assert np.array_equal(
        np.asarray([row.tokens for row in actual], dtype=np.float32),
        np.asarray([row.tokens for row in expected], dtype=np.float32),
    )
    assert np.array_equal(
        np.asarray([row.target for row in actual], dtype=np.float32),
        np.asarray([row.target for row in expected], dtype=np.float32),
    )
    assert tape_root == protocol["trajectory_tape_root"]
    assert episode_count == 16
    assert len(actual) > 0


@pytest.mark.parametrize("module_fixture", ["base_analysis", "base_verifier"])
def test_runtime_provenance_keeps_legacy_and_rejects_wrong_head(
    module_fixture, request, monkeypatch
) -> None:
    module = request.getfixturevalue(module_fixture)
    measurement = u004_evidence_protocol_v1()
    monkeypatch.setattr(
        module,
        "bound_clean_source_commit_v1",
        lambda _repository: measurement["source_commit"],
    )
    assert module._analysis_runtime_provenance_v1(
        SimpleNamespace(), measurement
    ) == {}

    monkeypatch.setattr(
        module, "bound_clean_source_commit_v1", lambda _repository: U005_COMMIT
    )
    explicit = SimpleNamespace(
        analysis_runtime_source_commit=U005_COMMIT,
        analysis_runtime_protocol_id="u005-protocol",
        analysis_runtime_execution_id="u005-execution",
    )
    assert module._analysis_runtime_provenance_v1(explicit, measurement) == {
        "measurement_protocol_id": measurement["protocol_id"],
        "measurement_source_commit": measurement["source_commit"],
        "analysis_runtime_protocol_id": "u005-protocol",
        "analysis_runtime_source_commit": U005_COMMIT,
        "analysis_runtime_execution_id": "u005-execution",
    }
    wrong = deepcopy(explicit)
    wrong.analysis_runtime_source_commit = "b" * 40
    with pytest.raises(Exception, match="clean .* runtime checkout"):
        module._analysis_runtime_provenance_v1(wrong, measurement)
    incomplete = SimpleNamespace(analysis_runtime_source_commit=U005_COMMIT)
    with pytest.raises(Exception, match="runtime authority is incomplete"):
        module._analysis_runtime_provenance_v1(incomplete, measurement)


def test_verifier_requires_exact_u005_protocol_and_execution_ids(
    successor_verifier, monkeypatch
) -> None:
    u005 = build_ratified_analysis_successor_protocol_v1(U005_COMMIT)
    exact = {
        "success": True,
        "measurement_protocol_id": U004_PROTOCOL_ID_V1,
        "measurement_source_commit": U004_SOURCE_COMMIT_V1,
        "analysis_runtime_protocol_id": u005["protocol_id"],
        "analysis_runtime_source_commit": U005_COMMIT,
        "analysis_runtime_execution_id": ANALYSIS_EXECUTION_ID_V1,
    }
    monkeypatch.setattr(successor_verifier, "_validate_runtime", lambda _args: u005)
    monkeypatch.setattr(successor_verifier._U004, "_verify", lambda _args: dict(exact))
    result = successor_verifier._verify(SimpleNamespace())
    assert all(result[key] == value for key, value in exact.items())
    for key in (
        "analysis_runtime_protocol_id",
        "analysis_runtime_source_commit",
        "analysis_runtime_execution_id",
    ):
        wrong = dict(exact)
        wrong[key] += ":wrong"
        monkeypatch.setattr(
            successor_verifier._U004, "_verify", lambda _args, row=wrong: row
        )
        with pytest.raises(
            successor_verifier.LearnedResourceForecastVerifierU005Error,
            match="both exact authorities",
        ):
            successor_verifier._verify(SimpleNamespace())


def _zero_hit_receipt(history, u005, manifest) -> dict:
    request = history._expected_request(u005, manifest, history.DEFAULT_SCAN_ROOT)
    return {
        "schema": history.SCHEMA_V1,
        "protocol_id": u005["protocol_id"],
        "source_commit": u005["source_commit"],
        "pilot_execution_identity": u005["pilot_execution_identity"],
        "analysis_execution_id": u005["analysis_execution_id"],
        "scan_root": request["scan_root"],
        "excluded_roots": request["excluded_roots"],
        "scanned_identity_tokens": request["execution_ids"],
        "new_training_execution_ids": [],
        "new_evidence_execution_ids": [],
        "new_tape_roots": [],
        "campaign_artifact_paths": request["campaign_artifact_paths"],
        "predecessor_authority_tokens_scanned_as_collisions": False,
        "hosts": [
            {
                "host_alias": alias,
                "expected_hostname": hostname,
                "actual_hostname": hostname,
                "scanned_path_count": 1,
                "match_count": 0,
                "matches": [],
            }
            for alias, hostname in history.HOSTS_V1
        ],
        "total_match_count": 0,
        "no_prior_identity_hits": True,
    }


def test_three_host_authority_receipt_is_exact_zero_hit(prepare, history) -> None:
    u005 = build_ratified_analysis_successor_protocol_v1(U005_COMMIT)
    manifest = prepare.build_launch_manifest_v1(u005)
    receipt = _zero_hit_receipt(history, u005, manifest)
    assert history.validate_authority_scan_receipt_v1(
        receipt, u005, manifest
    ) == receipt
    tampered = deepcopy(receipt)
    tampered["hosts"][1]["match_count"] = 1
    with pytest.raises(history.LearnedResourceForecastAnalysisHistoryU005Error):
        history.validate_authority_scan_receipt_v1(tampered, u005, manifest)


def test_u005_targets_are_one_shot_including_partial_retention(
    postprocess, tmp_path: Path
) -> None:
    roots = [tmp_path / "analysis", tmp_path / "status", tmp_path / "retained"]
    postprocess._require_fresh_targets_v1(*roots)
    for index in range(3):
        isolated = [
            tmp_path / f"case-{index}-analysis",
            tmp_path / f"case-{index}-status",
            tmp_path / f"case-{index}-retained",
        ]
        isolated[index].mkdir()
        with pytest.raises(
            postprocess.LearnedResourceForecastPostprocessU005Error,
            match="identity is consumed",
        ):
            postprocess._require_fresh_targets_v1(*isolated)


def test_failed_u004_boundary_requires_empty_analysis_and_absent_retention(
    postprocess, tmp_path: Path
) -> None:
    status = tmp_path / "u004-status.jsonl"
    analysis_root = tmp_path / "u004-analysis"
    retained_root = tmp_path / "u004-retained"
    analysis_root.mkdir()
    rows = [
        {
            "event": "POSTPROCESS_STARTED",
            "source_commit": U004_SOURCE_COMMIT_V1,
            "successor_protocol_id": U004_PROTOCOL_ID_V1,
        },
        {
            "event": "PREREQUISITES_COMPLETED",
            "predecessor_training_job_count": 144,
            "predecessor_model_snapshot_count": 432,
            "successor_evidence_job_count": 432,
        },
        {"event": "STAGE_STARTED", "stage": "FIT_ENCODERS"},
        {
            "event": "POSTPROCESS_FAILED",
            "failure_kind": "NameError",
            "failure_message": "name 'aligned_forecast_examples_v1' is not defined",
        },
    ]
    status.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )
    manifest = {
        "fixed_paths": {
            "postprocess_status": str(status),
            "analysis_root": str(analysis_root),
            "retained_root": str(retained_root),
        }
    }
    postprocess._validate_failed_u004_boundary(status, manifest)
    (analysis_root / "partial").write_text("x", encoding="utf-8")
    with pytest.raises(postprocess.LearnedResourceForecastPostprocessU005Error):
        postprocess._validate_failed_u004_boundary(status, manifest)
    (analysis_root / "partial").unlink()
    retained_root.mkdir()
    with pytest.raises(postprocess.LearnedResourceForecastPostprocessU005Error):
        postprocess._validate_failed_u004_boundary(status, manifest)


def test_retention_closes_at_exact_2064_plus_inventory(postprocess) -> None:
    categories = postprocess.expected_category_counts_v1()
    provenance = postprocess.expected_provenance_counts_v1()
    assert sum(categories.values()) == 2064
    assert sum(provenance.values()) == 2064
    assert postprocess.EXPECTED_RETAINED_ARTIFACT_COUNT_V1 == 2064
    assert postprocess.EXPECTED_PHYSICAL_FILE_COUNT_V1 == 2065
    assert provenance == {
        postprocess._U004_POSTPROCESS.PROVENANCE_U002_TRAINING_V1: 591,
        postprocess._U004_POSTPROCESS.PROVENANCE_U004_EVIDENCE_V1: 1456,
        postprocess._U004_POSTPROCESS.PROVENANCE_GATHER_V1: 2,
        postprocess._U004_POSTPROCESS.PROVENANCE_FAILED_U002_EVIDENCE_V1: 1,
        postprocess.PROVENANCE_U004_FAILURE_V1: 1,
        postprocess.PROVENANCE_U005_AUTHORITY_V1: 3,
        postprocess.PROVENANCE_U005_ANALYSIS_V1: 9,
        postprocess.PROVENANCE_U005_STATUS_V1: 1,
    }
    assert categories["u005_independent_verification"] == 1
    assert len(ANALYSIS_OUTPUT_FILENAMES_V1) == 9


def test_tampered_u005_protocol_or_identity_never_validates() -> None:
    protocol = build_ratified_analysis_successor_protocol_v1(U005_COMMIT)
    for key in ("protocol_id", "pilot_execution_identity", "analysis_execution_id"):
        tampered = deepcopy(protocol)
        tampered[key] += ":wrong"
        with pytest.raises(Exception):
            validate_ratified_analysis_successor_protocol_v1(tampered)
