from __future__ import annotations

from collections import OrderedDict
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from acfqp.science import (
    matched_double_dqn_2048_learned_resource_pilot_v1 as runtime,
)
from acfqp.science.learned_resource_forecast_2048_v1 import (
    load_generator_policy_snapshot_v1,
)
from acfqp.science.learned_resource_forecast_protocol_v1 import (
    LEARNED_RESOURCE_FORECAST_ARMS_V1,
    build_ratified_learned_resource_forecast_protocol_v1,
)
from acfqp.science.matched_double_dqn_2048_learned_resource_pilot_v1 import (
    LEARNED_RESOURCE_POLICY_TRAINING_RESULT_SCHEMA_V1,
    expected_policy_training_execution_id_v1,
    policy_checkpoint_filename_v1,
    run_learned_resource_policy_training_seed_arm_v1,
)


REPOSITORY = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPOSITORY / "scripts/run_learned_resource_policy_training_u002.py"
SOURCE_COMMIT = "6" * 40


def _load_script():
    spec = importlib.util.spec_from_file_location(
        "learned_resource_policy_training_cli", SCRIPT_PATH
    )
    if spec is None or spec.loader is None:
        raise AssertionError("cannot load learned-resource policy-training CLI")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _tiny_protocol() -> dict:
    protocol = build_ratified_learned_resource_forecast_protocol_v1(SOURCE_COMMIT)
    protocol["training"].update(
        {
            "environment_steps_per_seed_arm": 20,
            "evaluation_checkpoints": [20],
            "evaluation_episodes_per_checkpoint": 1,
            "replay_capacity": 64,
            "replay_warmup_environment_steps": 4,
            "batch_size": 4,
            "train_every_environment_steps": 4,
            "target_network_sync_environment_steps": 8,
        }
    )
    protocol["training"]["epsilon_schedule"]["decay_steps"] = 20
    return protocol


@pytest.mark.parametrize(
    ("arm", "expected_dimension", "expected_parameter_count"),
    [
        (LEARNED_RESOURCE_FORECAST_ARMS_V1[0], 16, 71_172),
        (LEARNED_RESOURCE_FORECAST_ARMS_V1[1], 32, 75_268),
        (LEARNED_RESOURCE_FORECAST_ARMS_V1[2], 32, 75_268),
    ],
)
def test_tiny_cpu_runtime_captures_bare_twenty_step_online_checkpoint(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    arm: str,
    expected_dimension: int,
    expected_parameter_count: int,
) -> None:
    torch = pytest.importorskip("torch")
    pytest.importorskip("numpy")
    protocol = _tiny_protocol()
    monkeypatch.setattr(
        runtime,
        "validate_ratified_learned_resource_forecast_protocol_v1",
        lambda value: value,
    )

    result, snapshots = run_learned_resource_policy_training_seed_arm_v1(
        protocol=protocol,
        arm=arm,
        seed=protocol["training_seeds"][0],
        device_name="cpu",
    )

    assert result["schema"] == LEARNED_RESOURCE_POLICY_TRAINING_RESULT_SCHEMA_V1
    assert result["training_environment_interactions"] == 20
    assert result["representation_telemetry"]["input_dimension"] == expected_dimension
    assert result["network_parameter_count"] == expected_parameter_count
    assert result["checkpoint_artifact_contract"][
        "separate_final_model_artifact_written"
    ] is False
    assert list(snapshots) == [20]
    assert type(snapshots[20]) is OrderedDict
    assert snapshots[20]
    assert all(type(name) is str for name in snapshots[20])
    assert all(
        type(value) is torch.Tensor and value.device.type == "cpu"
        for value in snapshots[20].values()
    )
    snapshot_path = tmp_path / "bare-online-state-dict.pt"
    torch.save(snapshots[20], snapshot_path)
    loaded = load_generator_policy_snapshot_v1(
        snapshot_path, arm=arm, device_name="cpu"
    )
    assert loaded.training is False


def test_execution_identity_and_checkpoint_filenames_are_exact() -> None:
    protocol = build_ratified_learned_resource_forecast_protocol_v1(SOURCE_COMMIT)
    arm = LEARNED_RESOURCE_FORECAST_ARMS_V1[2]
    seed = protocol["training_seeds"][0]
    assert expected_policy_training_execution_id_v1(
        protocol, arm=arm, seed=seed
    ) == (
        f"{protocol['pilot_execution_identity']}:policy-training:"
        f"{arm}:seed:{seed}"
    )
    assert policy_checkpoint_filename_v1(
        arm=arm, seed=seed, checkpoint=25_000
    ) == f"{arm.lower()}-seed-{seed}-checkpoint-25000.pt"


def test_cli_exclusively_writes_one_json_and_three_bare_checkpoints(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    torch = pytest.importorskip("torch")
    module = _load_script()
    protocol = build_ratified_learned_resource_forecast_protocol_v1(SOURCE_COMMIT)
    arm = protocol["arms"][0]
    seed = protocol["training_seeds"][0]
    protocol_path = tmp_path / "protocol.json"
    output_dir = tmp_path / "results"
    protocol_path.write_text(json.dumps(protocol), encoding="utf-8")
    snapshots = {
        checkpoint: OrderedDict(
            [("0.weight", torch.tensor([float(checkpoint)]))]
        )
        for checkpoint in protocol["training"]["evaluation_checkpoints"]
    }
    monkeypatch.setattr(
        module, "bound_clean_source_commit_v1", lambda _repository: SOURCE_COMMIT
    )
    monkeypatch.setattr(
        module,
        "run_learned_resource_policy_training_seed_arm_v1",
        lambda **_kwargs: (
            {
                "schema": LEARNED_RESOURCE_POLICY_TRAINING_RESULT_SCHEMA_V1,
                "policy_training_matrix_gate": "NOT_RUN_FIXTURE",
            },
            snapshots,
        ),
    )
    monkeypatch.setattr(
        module,
        "_runtime_context",
        lambda device: {"device": device, "runtime_fixture": True},
    )
    execution_id = expected_policy_training_execution_id_v1(
        protocol, arm=arm, seed=seed
    )
    args = SimpleNamespace(
        protocol=protocol_path,
        arm=arm,
        seed=seed,
        device="cpu",
        output_dir=output_dir,
        execution_id=execution_id,
    )

    summary = module._run(args)

    artifacts = sorted(path.name for path in output_dir.iterdir())
    assert len(artifacts) == 4
    assert len([name for name in artifacts if name.endswith(".json")]) == 1
    assert len([name for name in artifacts if name.endswith(".pt")]) == 3
    document = json.loads(Path(summary["result"]).read_text(encoding="utf-8"))
    rows = document["artifact_manifest"]["checkpoint_files"]
    assert [row["checkpoint_environment_interactions"] for row in rows] == [
        25_000,
        50_000,
        100_000,
    ]
    assert [row["filename"] for row in rows] == [
        policy_checkpoint_filename_v1(
            arm=arm, seed=seed, checkpoint=checkpoint
        )
        for checkpoint in (25_000, 50_000, 100_000)
    ]
    assert document["artifact_manifest"][
        "separate_final_model_artifact_written"
    ] is False
    for row in rows:
        loaded = torch.load(
            output_dir / row["filename"], map_location="cpu", weights_only=True
        )
        assert list(loaded) == ["0.weight"]

    with pytest.raises(
        module.LearnedResourcePolicyTrainingCLIError, match="identity is consumed"
    ):
        module._run(args)


def test_cli_rejects_foreign_execution_identity() -> None:
    module = _load_script()
    protocol = build_ratified_learned_resource_forecast_protocol_v1(SOURCE_COMMIT)
    with pytest.raises(
        module.LearnedResourcePolicyTrainingCLIError, match="execution ID differs"
    ):
        module._validate_execution_request(
            protocol=protocol,
            source_commit=SOURCE_COMMIT,
            arm=protocol["arms"][0],
            seed=protocol["training_seeds"][0],
            device="cpu",
            execution_id="foreign",
        )
