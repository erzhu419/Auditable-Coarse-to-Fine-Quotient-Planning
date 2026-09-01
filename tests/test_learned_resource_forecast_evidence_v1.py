from __future__ import annotations

import importlib.util
import io
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from acfqp.science import learned_resource_forecast_evidence_v1 as subject
from acfqp.science.learned_resource_forecast_protocol_v1 import (
    LEARNED_RESOURCE_FORECAST_ARMS_V1,
    LEARNED_RESOURCE_FORECAST_TEST_SEEDS_V1,
    LEARNED_RESOURCE_FORECAST_TRAIN_SEEDS_V1,
    build_ratified_learned_resource_forecast_protocol_v1,
    player_key_v1,
)
from acfqp.science.matched_double_dqn_2048_learned_resource_pilot_v1 import (
    policy_checkpoint_filename_v1,
)


REPOSITORY = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPOSITORY / "scripts/run_learned_resource_player_evidence_u002.py"
SOURCE_COMMIT = "7" * 40


def _load_script():
    spec = importlib.util.spec_from_file_location(
        "learned_resource_player_evidence_cli", SCRIPT_PATH
    )
    if spec is None or spec.loader is None:
        raise AssertionError("cannot load learned-resource player-evidence CLI")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _first_legal(_state, mask: tuple[bool, bool, bool, bool]) -> int:
    return next(index for index, allowed in enumerate(mask) if allowed)


def _context(protocol, *, seed: int, arm: str, checkpoint: int) -> dict:
    return {
        "execution_id": subject.expected_player_evidence_execution_id_v1(
            protocol,
            base_seed=seed,
            generator_arm=arm,
            checkpoint=checkpoint,
        ),
        "source_commit": SOURCE_COMMIT,
        "hostname": "evidence-test-host",
        "device": "cpu",
    }


@pytest.fixture(scope="module")
def protocol():
    return build_ratified_learned_resource_forecast_protocol_v1(SOURCE_COMMIT)


@pytest.fixture(scope="module")
def train_artifacts(protocol):
    seed = LEARNED_RESOURCE_FORECAST_TRAIN_SEEDS_V1[0]
    arm = LEARNED_RESOURCE_FORECAST_ARMS_V1[0]
    checkpoint = 25_000
    return subject._collect_player_evidence_with_selector_v1(
        protocol=protocol,
        action_selector=_first_legal,
        base_seed=seed,
        generator_arm=arm,
        checkpoint=checkpoint,
        execution_context=_context(
            protocol, seed=seed, arm=arm, checkpoint=checkpoint
        ),
        snapshot_reference="/server/models/train-player.pt",
        trajectory_episode_count=2,
        label_episode_count=3,
        probe_count=2,
    )


@pytest.fixture(scope="module")
def test_artifacts(protocol):
    seed = LEARNED_RESOURCE_FORECAST_TEST_SEEDS_V1[0]
    arm = LEARNED_RESOURCE_FORECAST_ARMS_V1[1]
    checkpoint = 50_000
    return subject._collect_player_evidence_with_selector_v1(
        protocol=protocol,
        action_selector=_first_legal,
        base_seed=seed,
        generator_arm=arm,
        checkpoint=checkpoint,
        execution_context=_context(
            protocol, seed=seed, arm=arm, checkpoint=checkpoint
        ),
        snapshot_reference="/server/models/test-player.pt",
        trajectory_episode_count=0,
        label_episode_count=2,
        probe_count=1,
    )


def test_execution_identity_artifact_names_and_matched_lane_roots(protocol) -> None:
    seed = LEARNED_RESOURCE_FORECAST_TRAIN_SEEDS_V1[0]
    other_seed = LEARNED_RESOURCE_FORECAST_TEST_SEEDS_V1[0]
    arm = LEARNED_RESOURCE_FORECAST_ARMS_V1[2]
    checkpoint = 100_000
    assert subject.expected_player_evidence_execution_id_v1(
        protocol,
        base_seed=seed,
        generator_arm=arm,
        checkpoint=checkpoint,
    ) == (
        f"{protocol['pilot_execution_identity']}:player-evidence:"
        f"{arm}:seed:{seed}:checkpoint:{checkpoint}"
    )
    stem = f"{arm.lower()}-seed-{seed}-checkpoint-{checkpoint}"
    assert subject.player_evidence_artifact_basenames_v1(
        base_seed=seed, generator_arm=arm, checkpoint=checkpoint
    ) == {
        "trajectory_json": f"{stem}.trajectory.json",
        "trajectory_npz": f"{stem}.trajectory.npz",
        "label_json": f"{stem}.label.json",
        "probe_json": f"{stem}.probe.json",
    }

    first_roots = subject._lane_tape_roots_v1(
        protocol, player_key=player_key_v1(seed, arm, checkpoint)
    )
    second_roots = subject._lane_tape_roots_v1(
        protocol, player_key=player_key_v1(other_seed, arm, checkpoint)
    )
    assert first_roots == second_roots == {
        "trajectory": protocol["trajectory_tape_root"],
        "label": protocol["label_tape_root"],
        "probe": protocol["probe_tape_root"],
    }
    assert len(set(first_roots.values())) == 3


def test_train_player_has_strictly_separated_trajectory_label_and_probe_artifacts(
    protocol, train_artifacts
) -> None:
    assert train_artifacts.is_train_player is True
    trajectory = train_artifacts.trajectory_document
    assert trajectory is not None
    label = train_artifacts.label_document
    probe = train_artifacts.probe_document
    assert trajectory["schema"] == subject.TRAJECTORY_EVIDENCE_SCHEMA_V1
    assert label["schema"] == subject.LABEL_EVIDENCE_SCHEMA_V1
    assert probe["schema"] == subject.PROBE_EVIDENCE_SCHEMA_V1
    assert trajectory["complete_episode_count"] == 2
    assert label["complete_episode_count"] == 3
    assert probe["probe_count"] == 2
    assert 0 < len(train_artifacts.trajectory_examples) <= 64
    assert trajectory["forecast_example_count"] == len(
        train_artifacts.trajectory_examples
    )
    assert all(
        example.key.player_id
        == trajectory["player_identity"]["player_key"]
        for example in train_artifacts.trajectory_examples
    )

    assert "skill_score" not in trajectory
    assert "probe_rows" not in trajectory
    assert "forecast_example_count" not in label
    assert "probe_rows" not in label
    assert "skill_score" not in probe
    assert "complete_episode_summaries" not in probe
    assert trajectory["skill_label_file_opened"] is False
    assert label["skill_score"]["episode_count"] == 3
    assert label["skill_score"]["mean_total_merge_score"] == pytest.approx(
        label["skill_score"]["total_merge_score_sum"] / 3
    )
    for row in trajectory["complete_episode_summaries"]:
        assert row["goal_terminated_episode"] is True
        assert len(row["initial_board"]) == len(row["terminal_board"]) == 16
        assert len(row["accepted_action_indices"]) == row["decision_count"]
        assert all(action in range(4) for action in row["accepted_action_indices"])
    for row in label["complete_episode_summaries"]:
        assert row["goal_terminated_episode"] is True
        assert row["terminal_status"] in ("WON", "LOST")
        assert len(row["accepted_action_indices"]) == row["decision_count"]
        assert all(action in range(4) for action in row["accepted_action_indices"])
    for row in probe["probe_rows"]:
        assert len(row["boards_s0_through_s8"]) == 9
        assert all(len(board) == 16 for board in row["boards_s0_through_s8"])
        assert len(row["action_indices_a0_through_a7"]) == 8
        assert len(row["merge_scores"]) == 8
        assert row["later_state_or_episode_outcome_included"] is False
    assert trajectory["trajectory_tape_root"] == protocol["trajectory_tape_root"]
    assert label["label_tape_root"] == protocol["label_tape_root"]
    assert probe["probe_tape_root"] == protocol["probe_tape_root"]


def test_train_forecast_examples_serialize_as_exact_compressed_float32_npz(
    train_artifacts,
) -> None:
    np = pytest.importorskip("numpy")
    raw = subject.forecast_examples_npz_bytes_v1(
        train_artifacts.trajectory_examples
    )
    with np.load(io.BytesIO(raw), allow_pickle=False) as arrays:
        assert set(arrays.files) == {
            "tokens",
            "targets",
            "episode_index",
            "window_start",
        }
        count = len(train_artifacts.trajectory_examples)
        assert arrays["tokens"].shape == (count, 8, 21)
        assert arrays["targets"].shape == (count, 54)
        assert arrays["episode_index"].shape == (count,)
        assert arrays["window_start"].shape == (count,)
        assert arrays["tokens"].dtype == np.float32
        assert arrays["targets"].dtype == np.float32
        assert arrays["episode_index"].dtype == np.int64
        assert arrays["window_start"].dtype == np.int64
        assert bool(np.isfinite(arrays["tokens"]).all())
        assert bool(np.isfinite(arrays["targets"]).all())


def test_test_player_never_generates_trajectory_metadata_or_arrays(
    protocol, test_artifacts
) -> None:
    assert test_artifacts.is_train_player is False
    assert test_artifacts.trajectory_document is None
    assert test_artifacts.trajectory_examples == ()
    assert test_artifacts.label_document["complete_episode_count"] == 2
    assert test_artifacts.probe_document["probe_count"] == 1
    assert test_artifacts.label_document["player_identity"]["split"] == "TEST"
    assert test_artifacts.probe_document["player_identity"]["split"] == "TEST"
    with pytest.raises(subject.LearnedResourceForecastEvidenceV1Error):
        subject.forecast_examples_npz_bytes_v1(())


def test_cli_exclusively_writes_separated_train_artifacts_without_label_summary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    protocol,
    train_artifacts,
) -> None:
    module = _load_script()
    seed = LEARNED_RESOURCE_FORECAST_TRAIN_SEEDS_V1[0]
    arm = LEARNED_RESOURCE_FORECAST_ARMS_V1[0]
    checkpoint = 25_000
    protocol_path = tmp_path / "protocol.json"
    protocol_path.write_text(json.dumps(protocol), encoding="utf-8")
    snapshot = tmp_path / policy_checkpoint_filename_v1(
        arm=arm, seed=seed, checkpoint=checkpoint
    )
    snapshot.write_bytes(b"strict-loader-is-mocked-in-cli-test")
    output_dir = tmp_path / "train-evidence"
    execution_id = subject.expected_player_evidence_execution_id_v1(
        protocol,
        base_seed=seed,
        generator_arm=arm,
        checkpoint=checkpoint,
    )
    monkeypatch.setattr(
        module, "bound_clean_source_commit_v1", lambda _repository: SOURCE_COMMIT
    )
    monkeypatch.setattr(
        module,
        "_runtime_context",
        lambda device: {"hostname": "cli-test", "device": device},
    )
    monkeypatch.setattr(
        module,
        "collect_registered_player_evidence_v1",
        lambda **_kwargs: train_artifacts,
    )
    args = SimpleNamespace(
        protocol=protocol_path,
        snapshot=snapshot,
        arm=arm,
        seed=seed,
        checkpoint=checkpoint,
        device="cpu",
        output_dir=output_dir,
        execution_id=execution_id,
    )

    summary = module._run(args)

    assert summary["artifact_count"] == 4
    assert summary["label_content_in_summary"] is False
    assert "mean_total_merge_score" not in json.dumps(summary, sort_keys=True)
    assert sorted(path.suffix for path in output_dir.iterdir()) == [
        ".json",
        ".json",
        ".json",
        ".npz",
    ]
    paths = {name: Path(path) for name, path in summary["artifact_paths"].items()}
    trajectory = json.loads(paths["trajectory_json"].read_text(encoding="utf-8"))
    label = json.loads(paths["label_json"].read_text(encoding="utf-8"))
    probe = json.loads(paths["probe_json"].read_text(encoding="utf-8"))
    assert trajectory["artifact_manifest"]["contains_other_lane_content"] is False
    assert label["artifact_manifest"]["contains_other_lane_content"] is False
    assert probe["artifact_manifest"]["contains_other_lane_content"] is False
    assert "skill_score" not in trajectory
    assert "probe_rows" not in label
    assert "skill_score" not in probe

    with pytest.raises(
        module.LearnedResourcePlayerEvidenceCLIError, match="identity is consumed"
    ):
        module._run(args)


def test_cli_test_player_writes_only_label_and_probe(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    protocol,
    test_artifacts,
) -> None:
    module = _load_script()
    seed = LEARNED_RESOURCE_FORECAST_TEST_SEEDS_V1[0]
    arm = LEARNED_RESOURCE_FORECAST_ARMS_V1[1]
    checkpoint = 50_000
    protocol_path = tmp_path / "protocol.json"
    protocol_path.write_text(json.dumps(protocol), encoding="utf-8")
    snapshot = tmp_path / policy_checkpoint_filename_v1(
        arm=arm, seed=seed, checkpoint=checkpoint
    )
    snapshot.write_bytes(b"strict-loader-is-mocked-in-cli-test")
    execution_id = subject.expected_player_evidence_execution_id_v1(
        protocol,
        base_seed=seed,
        generator_arm=arm,
        checkpoint=checkpoint,
    )
    monkeypatch.setattr(
        module, "bound_clean_source_commit_v1", lambda _repository: SOURCE_COMMIT
    )
    monkeypatch.setattr(
        module,
        "_runtime_context",
        lambda device: {"hostname": "cli-test", "device": device},
    )
    monkeypatch.setattr(
        module,
        "collect_registered_player_evidence_v1",
        lambda **_kwargs: test_artifacts,
    )
    args = SimpleNamespace(
        protocol=protocol_path,
        snapshot=snapshot,
        arm=arm,
        seed=seed,
        checkpoint=checkpoint,
        device="cpu",
        output_dir=tmp_path / "test-evidence",
        execution_id=execution_id,
    )

    summary = module._run(args)

    assert summary["artifact_count"] == 2
    assert set(summary["artifact_paths"]) == {"label_json", "probe_json"}
    assert summary["trajectory_example_count"] == 0
    assert all(
        ".trajectory." not in path.name
        for path in (tmp_path / "test-evidence").iterdir()
    )


def test_cli_rejects_foreign_execution_id_and_snapshot_name(
    tmp_path: Path, protocol
) -> None:
    module = _load_script()
    seed = LEARNED_RESOURCE_FORECAST_TRAIN_SEEDS_V1[0]
    arm = LEARNED_RESOURCE_FORECAST_ARMS_V1[0]
    checkpoint = 25_000
    wrong_snapshot = tmp_path / "wrong.pt"
    wrong_snapshot.write_bytes(b"not-opened")
    with pytest.raises(
        module.LearnedResourcePlayerEvidenceCLIError,
        match="execution ID differs",
    ):
        module._validate_execution_request(
            protocol=protocol,
            source_commit=SOURCE_COMMIT,
            snapshot=wrong_snapshot,
            arm=arm,
            seed=seed,
            checkpoint=checkpoint,
            device="cpu",
            execution_id="foreign",
        )
    with pytest.raises(
        module.LearnedResourcePlayerEvidenceCLIError,
        match="snapshot path or filename",
    ):
        module._validate_execution_request(
            protocol=protocol,
            source_commit=SOURCE_COMMIT,
            snapshot=wrong_snapshot,
            arm=arm,
            seed=seed,
            checkpoint=checkpoint,
            device="cpu",
            execution_id=subject.expected_player_evidence_execution_id_v1(
                protocol,
                base_seed=seed,
                generator_arm=arm,
                checkpoint=checkpoint,
            ),
        )
