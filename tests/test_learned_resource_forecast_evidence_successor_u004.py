from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from acfqp.science import learned_resource_forecast_evidence_v1 as evidence
from acfqp.science.learned_resource_forecast_evidence_successor_protocol_v1 import (
    ABANDONED_U003_EXECUTION_IDENTITY_V1,
    ABANDONED_U003_PROTOCOL_ID_V1,
    ABANDONED_U003_SOURCE_COMMIT_V1,
    U002_PROTOCOL_ID_V1,
    U002_SOURCE_COMMIT_V1,
    build_ratified_learned_resource_forecast_evidence_successor_protocol_v1,
    validate_ratified_learned_resource_forecast_evidence_successor_protocol_v1,
)
from acfqp.science.learned_resource_forecast_protocol_v1 import (
    LEARNED_RESOURCE_FORECAST_ARMS_V1,
    LEARNED_RESOURCE_FORECAST_TRAIN_SEEDS_V1,
    MODEL_EVALUATION_TAPE_PREFIX_V1,
    build_ratified_learned_resource_forecast_protocol_v1,
)
from acfqp.science.matched_double_dqn_2048_learned_resource_pilot_v1 import (
    expected_policy_training_execution_id_v1,
    policy_checkpoint_filename_v1,
)


REPOSITORY = Path(__file__).resolve().parents[1]
SOURCE_COMMIT = "a" * 40


def _load_script(filename: str):
    path = REPOSITORY / "scripts" / filename
    spec = importlib.util.spec_from_file_location(filename.replace(".", "_"), path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def protocol() -> dict:
    return build_ratified_learned_resource_forecast_evidence_successor_protocol_v1(
        SOURCE_COMMIT
    )


@pytest.fixture(scope="module")
def manifest(protocol: dict) -> dict:
    prepare = _load_script(
        "prepare_learned_resource_forecast_evidence_successor_u004.py"
    )
    return prepare.build_launch_manifest_v1(protocol)


def _first_legal(_state, mask: tuple[bool, bool, bool, bool]) -> int:
    return next(index for index, allowed in enumerate(mask) if allowed)


def _context(protocol: dict, seed: int, arm: str, checkpoint: int) -> dict:
    return {
        "execution_id": evidence.expected_player_evidence_execution_id_v1(
            protocol,
            base_seed=seed,
            generator_arm=arm,
            checkpoint=checkpoint,
        ),
        "source_commit": protocol["source_commit"],
        "hostname": "equivalence-host",
        "device": "cpu",
    }


def _numeric_lane(document: dict) -> dict:
    result = dict(document)
    for key in (
        "protocol_id",
        "source_commit",
        "pilot_execution_identity",
        "execution_context",
        "trajectory_tape_root",
        "label_tape_root",
        "probe_tape_root",
    ):
        result.pop(key, None)
    return result


def test_protocol_is_exact_evidence_only_successor_with_three_fresh_roots(
    protocol: dict,
) -> None:
    assert validate_ratified_learned_resource_forecast_evidence_successor_protocol_v1(
        protocol
    ) == protocol
    assert protocol["fresh_successor_boundary"] == {
        "predecessor_execution_identity": (
            "acfqp-learned-resource-forecast-2048-pilot-u002-ordinal2-attempt1"
        ),
        "predecessor_ordinal": 2,
        "predecessor_attempt": 1,
        "successor_ordinal": 4,
        "successor_attempt": 1,
        "predecessor_training_population_reused_read_only": True,
        "predecessor_training_execution_ids_retried": False,
        "predecessor_failed_evidence_dispatch_identity_retried": False,
        "predecessor_evidence_outputs_reused": False,
        "successor_evidence_execution_ids_are_all_fresh": True,
        "successor_trajectory_label_probe_tapes_are_all_fresh": True,
        "successor_model_evaluation_tape_is_fresh": False,
        "model_evaluation_measurement_inherited_from_u002": True,
        "method_gate_split_classifier_encoder_and_bootstrap_changed": False,
    }
    parent = protocol["predecessor_training_authority"]
    assert parent["protocol_id"] == U002_PROTOCOL_ID_V1
    assert parent["source_commit"] == U002_SOURCE_COMMIT_V1
    assert parent["completed_training_jobs"] == 144
    assert parent["model_snapshots"] == 432
    assert parent["training_artifacts_are_read_only_inputs"] is True
    assert parent["training_artifacts_may_be_relabelled_as_u004"] is False
    assert parent["model_evaluation_tape_prefix"] == MODEL_EVALUATION_TAPE_PREFIX_V1
    assert parent["model_evaluation_measurements_are_read_only_inputs"] is True
    assert parent["model_evaluation_reexecuted_in_u004"] is False
    assert protocol["execution_contract"]["phase_roster"] == ["evidence"]
    assert protocol["execution_contract"]["policy_training_execution_id_template"] is None
    assert protocol["evaluation_tape_prefix"] == MODEL_EVALUATION_TAPE_PREFIX_V1
    fresh_roots = (
        protocol["trajectory_tape_root"],
        protocol["label_tape_root"],
        protocol["probe_tape_root"],
    )
    assert len(set(fresh_roots)) == 3
    assert all("u004" in value for value in fresh_roots)
    assert protocol["evaluation_tape_prefix"] not in fresh_roots
    assert protocol["tape_independence_contract"] == {
        "pairwise_distinct_roots": [
            protocol["training_tape_prefix"],
            protocol["evaluation_tape_prefix"],
            *fresh_roots,
        ],
        "training_tape_root_is_read_only_u002_predecessor": True,
        "model_evaluation_tape_root_is_read_only_u002_predecessor": True,
        "model_evaluation_tape_root_is_fresh_u004": False,
        "model_evaluation_reexecuted_in_u004": False,
        "trajectory_label_probe_roots_are_fresh_u004": True,
        "fresh_u004_roots": list(fresh_roots),
        "read_only_u002_roots": [
            protocol["training_tape_prefix"],
            protocol["evaluation_tape_prefix"],
        ],
        "u002_evidence_tapes_or_artifacts_reused": False,
        "abandoned_u003_evidence_tapes_or_artifacts_reused": False,
    }
    assert protocol["abandoned_u003_boundary"] == {
        "source_commit": ABANDONED_U003_SOURCE_COMMIT_V1,
        "protocol_id": ABANDONED_U003_PROTOCOL_ID_V1,
        "pilot_execution_identity": ABANDONED_U003_EXECUTION_IDENTITY_V1,
        "protocol_and_manifest_prepared_and_deployed": True,
        "history_scan_executed": False,
        "dispatch_identity_consumed": False,
        "evidence_jobs_executed": 0,
        "evidence_artifacts_eligible_for_u004": False,
        "abandonment_reason": (
            "MODEL_EVALUATION_TAPE_WAS_FALSELY_DECLARED_FRESH_BUT_NOT_REEXECUTED"
        ),
    }


def test_gate_split_classifier_encoder_and_bootstrap_are_byte_level_unchanged(
    protocol: dict,
) -> None:
    predecessor = build_ratified_learned_resource_forecast_protocol_v1(
        U002_SOURCE_COMMIT_V1
    )
    for key in (
        "arms",
        "training_seeds",
        "training_seed_split",
        "representation_arms",
        "representation_dimensions",
        "raw_prefix_contract",
        "self_supervised_trajectory_contract",
        "skill_label_contract",
        "probe_contract",
        "forecast_encoder_contract",
        "classifier_contract",
        "bootstrap_contract",
        "provisional_design_signal_contract",
    ):
        assert protocol[key] == predecessor[key]


def test_manifest_closes_separate_parent_and_successor_rosters(
    protocol: dict, manifest: dict
) -> None:
    assert manifest["phase_roster"] == ["evidence"]
    assert manifest["expected_counts"] == {
        "parent_policy_training_jobs": 144,
        "parent_model_snapshots": 432,
        "successor_player_evidence_jobs": 432,
        "trajectory_player_artifacts": 288,
        "complete_trajectory_episodes": 4608,
        "label_aggregates": 432,
        "exact_eight_action_probe_records": 6912,
    }
    parent_ids = {
        job["execution_id"]
        for worker in manifest["workers"]
        for job in worker["predecessor_policy_training_jobs"]
    }
    evidence_ids = {
        job["execution_id"]
        for worker in manifest["workers"]
        for job in worker["player_evidence_jobs"]
    }
    assert len(parent_ids) == 144
    assert len(evidence_ids) == 432
    assert all(":policy-training:" in value and "u002" in value for value in parent_ids)
    assert all(":player-evidence:" in value and "u004" in value for value in evidence_ids)
    assert parent_ids.isdisjoint(evidence_ids)
    for worker in manifest["workers"]:
        assert len(worker["predecessor_policy_training_jobs"]) == 24
        assert len(worker["player_evidence_jobs"]) == 72
        assert worker["predecessor_snapshot_root"] != worker[
            "successor_evidence_output_root"
        ]
        assert "u002-results" in worker["predecessor_snapshot_root"]
        assert "u004-results" in worker["successor_evidence_output_root"]
    assert manifest["history_scan_contract"][
        "predecessor_authority_tokens_are_expected_existing_inputs"
    ] is True


def test_u004_reuses_exact_u002_numeric_measurement_logic_under_same_tapes(
    monkeypatch: pytest.MonkeyPatch,
    protocol: dict,
) -> None:
    u002 = build_ratified_learned_resource_forecast_protocol_v1("b" * 40)
    seed = LEARNED_RESOURCE_FORECAST_TRAIN_SEEDS_V1[0]
    arm = LEARNED_RESOURCE_FORECAST_ARMS_V1[0]
    checkpoint = 25_000
    original_full = evidence.collect_full_game_v1
    original_prefix = evidence.collect_prefix_v1
    monkeypatch.setattr(
        evidence,
        "collect_full_game_v1",
        lambda selector, *, tape_root, episode_index: original_full(
            selector, tape_root="u002-u004-equivalence-tape", episode_index=episode_index
        ),
    )
    monkeypatch.setattr(
        evidence,
        "collect_prefix_v1",
        lambda selector, *, tape_root, episode_index: original_prefix(
            selector, tape_root="u002-u004-equivalence-tape", episode_index=episode_index
        ),
    )
    common = {
        "action_selector": _first_legal,
        "base_seed": seed,
        "generator_arm": arm,
        "checkpoint": checkpoint,
        "snapshot_reference": "/immutable/u002/same-snapshot.pt",
        "trajectory_episode_count": 1,
        "label_episode_count": 1,
        "probe_count": 1,
    }
    before = evidence._collect_player_evidence_with_selector_v1(
        protocol=u002,
        execution_context=_context(u002, seed, arm, checkpoint),
        **common,
    )
    successor = evidence._collect_player_evidence_with_selector_v1(
        protocol=protocol,
        execution_context=_context(protocol, seed, arm, checkpoint),
        **common,
    )
    assert before.trajectory_examples == successor.trajectory_examples
    assert _numeric_lane(before.trajectory_document) == _numeric_lane(
        successor.trajectory_document
    )
    assert _numeric_lane(before.label_document) == _numeric_lane(
        successor.label_document
    )
    assert _numeric_lane(before.probe_document) == _numeric_lane(
        successor.probe_document
    )


def test_player_cli_writes_dual_provenance_without_mutating_parent_snapshot(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    protocol: dict,
) -> None:
    module = _load_script("run_learned_resource_player_evidence_u004.py")
    predecessor = build_ratified_learned_resource_forecast_protocol_v1(
        U002_SOURCE_COMMIT_V1
    )
    assert predecessor["protocol_id"] == U002_PROTOCOL_ID_V1
    seed = LEARNED_RESOURCE_FORECAST_TRAIN_SEEDS_V1[0]
    arm = LEARNED_RESOURCE_FORECAST_ARMS_V1[0]
    checkpoint = 25_000
    artifacts = evidence._collect_player_evidence_with_selector_v1(
        protocol=protocol,
        action_selector=_first_legal,
        base_seed=seed,
        generator_arm=arm,
        checkpoint=checkpoint,
        execution_context=_context(protocol, seed, arm, checkpoint),
        snapshot_reference="/immutable/u002/snapshot.pt",
        trajectory_episode_count=1,
        label_episode_count=1,
        probe_count=1,
    )
    protocol_path = tmp_path / "u004-protocol.json"
    parent_path = tmp_path / "u002-protocol.json"
    protocol_path.write_text(json.dumps(protocol), encoding="utf-8")
    parent_path.write_text(json.dumps(predecessor), encoding="utf-8")
    snapshot = tmp_path / policy_checkpoint_filename_v1(
        arm=arm, seed=seed, checkpoint=checkpoint
    )
    snapshot.write_bytes(b"unchanged-parent-snapshot")
    before = snapshot.read_bytes()
    monkeypatch.setattr(module, "bound_clean_source_commit_v1", lambda _repo: SOURCE_COMMIT)
    monkeypatch.setattr(
        module, "_runtime_context", lambda device: {"hostname": "test", "device": device}
    )
    monkeypatch.setattr(
        module, "collect_registered_player_evidence_v1", lambda **_kwargs: artifacts
    )
    training_id = expected_policy_training_execution_id_v1(
        predecessor, arm=arm, seed=seed
    )
    summary = module._run(
        SimpleNamespace(
            protocol=protocol_path,
            predecessor_protocol=parent_path,
            snapshot=snapshot,
            arm=arm,
            seed=seed,
            checkpoint=checkpoint,
            device="cpu",
            output_dir=tmp_path / "evidence",
            execution_id=evidence.expected_player_evidence_execution_id_v1(
                protocol,
                base_seed=seed,
                generator_arm=arm,
                checkpoint=checkpoint,
            ),
            predecessor_training_execution_id=training_id,
        )
    )
    assert snapshot.read_bytes() == before
    assert summary["predecessor_protocol_id"] == U002_PROTOCOL_ID_V1
    for key in ("label_json", "probe_json", "trajectory_json"):
        document = json.loads(
            Path(summary["artifact_paths"][key]).read_text(encoding="utf-8")
        )
        provenance = document["policy_snapshot"]
        assert provenance["predecessor_protocol_id"] == U002_PROTOCOL_ID_V1
        assert provenance["predecessor_source_commit"] == U002_SOURCE_COMMIT_V1
        assert provenance["predecessor_training_execution_id"] == training_id
        assert provenance["snapshot_is_read_only_predecessor_input"] is True
        assert provenance["snapshot_is_u004_training_artifact"] is False


def test_launcher_disables_ssh_multiplexing_and_never_retries(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_script("launch_learned_resource_forecast_evidence_successor_u004.py")
    seen = {}

    def fake_run(command, **kwargs):
        seen["command"] = command
        return SimpleNamespace(returncode=0, stdout="123\n", stderr="")

    monkeypatch.setattr(module.subprocess, "run", fake_run)
    assert module._ssh_dispatch("jtl110gpu2", "true") == "123"
    command = seen["command"]
    assert command[:2] == ["ssh", "-o"]
    assert "ControlMaster=no" in command
    assert "ControlPath=none" in command
    assert command.count("jtl110gpu2") == 1
    assert "retry" not in " ".join(command).lower()


def test_launcher_global_preflight_is_read_only_and_binds_both_roots(
    manifest: dict,
) -> None:
    module = _load_script("launch_learned_resource_forecast_evidence_successor_u004.py")
    fixed = manifest["fixed_paths"]
    worker = {
        **manifest["workers"][0],
        "_fixed_predecessor_protocol": fixed["predecessor_protocol"],
        "_fixed_predecessor_manifest": fixed["predecessor_manifest"],
    }
    command = module._remote_global_preflight_command(
        worker=worker,
        protocol_path=Path(fixed["protocol"]),
        manifest_path=Path(fixed["manifest"]),
        source_checkout=Path(fixed["source_checkout"]),
        source_pythonpath=Path(fixed["source_pythonpath"]),
        results_root=Path(fixed["results_root"]),
        status_root=Path(fixed["status_root"]),
        log_root=Path(fixed["log_root"]),
    )
    assert "--global-preflight-only" in command
    assert f"--predecessor-results-root {worker['predecessor_snapshot_root']}" in command
    assert f"--results-root {fixed['results_root']}/worker-0" in command
    assert "mkdir" not in command
    assert "nohup" not in command
    assert ">" not in command


def test_launcher_accepts_only_exact_zero_worker_u002_failure_history(
    tmp_path: Path,
) -> None:
    module = _load_script("launch_learned_resource_forecast_evidence_successor_u004.py")
    path = tmp_path / "u002-failed-evidence.jsonl"
    rows = [
        {"event": "GLOBAL_PRECHECK_COMPLETED", "phase": "evidence"},
        {"event": "DISPATCH_STARTED", "phase": "evidence"},
        {"event": "WORKER_DISPATCH_FAILED", "phase": "evidence", "worker": 0},
        {
            "event": "DISPATCH_FAILED",
            "phase": "evidence",
            "dispatched_worker_count": 0,
        },
    ]
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    module._validate_failed_u002_evidence_dispatch(path)
    rows[-1]["dispatched_worker_count"] = 1
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    with pytest.raises(
        module.LearnedResourceForecastEvidenceSuccessorLauncherV1Error,
        match="0-worker failure",
    ):
        module._validate_failed_u002_evidence_dispatch(path)


def test_history_roster_scans_only_432_fresh_evidence_ids(
    protocol: dict, manifest: dict
) -> None:
    module = _load_script("scan_learned_resource_forecast_history_u004.py")
    request = module._expected_scan_request(protocol, manifest, Path("/home/erzhu419/mine_code"))
    assert len(request["execution_ids"]) == 432
    assert len(set(request["execution_ids"])) == 432
    assert all("u004" in value for value in request["execution_ids"])
    assert len(request["tape_roots"]) == 3
    assert all("u004" in value for value in request["tape_roots"])
    assert protocol["evaluation_tape_prefix"] not in request["tape_roots"]
    contract = manifest["history_scan_contract"]
    assert contract["model_evaluation_tape_is_fresh"] is False
    assert contract["model_evaluation_tape_is_scanned_as_fresh"] is False
    assert contract["read_only_predecessor_tape_roots"] == [
        protocol["training_tape_prefix"],
        protocol["evaluation_tape_prefix"],
    ]
    assert U002_PROTOCOL_ID_V1 not in request["execution_ids"]


def test_worker_evidence_roster_counts_are_derived_from_split_ownership(
    manifest: dict,
) -> None:
    module = _load_script("run_learned_resource_forecast_worker_u004.py")
    assert [len(module._expected_evidence_names(worker)) for worker in manifest["workers"]] == [
        252,
        252,
        234,
        234,
        234,
        234,
    ]
