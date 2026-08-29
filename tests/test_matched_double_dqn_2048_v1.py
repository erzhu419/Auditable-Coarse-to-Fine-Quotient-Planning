from __future__ import annotations

import pytest

from acfqp.science.latent_resource_protocol_v1 import build_pilot_protocol_v1
from acfqp.science.matched_2048_env_v1 import initial_state_v1
from acfqp.science import matched_double_dqn_2048_v1 as runtime
from acfqp.science.matched_double_dqn_2048_v1 import (
    NETWORK_PARAMETER_COUNT_V1,
    MatchedDoubleDQN2048V1Error,
    epsilon_at_interaction_v1,
    observation_vector_v1,
    reward_from_merge_score_v1,
    run_pilot_seed_arm_v1,
)
from acfqp.science.sample_ledger_v1 import EvidenceClass, EvidenceLane, SampleLedgerV1


def test_matched_observations_have_the_same_dimension() -> None:
    state = initial_state_v1(seed="unit", episode_index=0)
    raw = observation_vector_v1(state, "RAW_BOARD")
    resource = observation_vector_v1(state, "RESOURCE_STATE_ONLY")

    assert len(raw) == len(resource) == 16
    assert all(0.0 <= value <= 1.0 for value in raw)
    assert all(-1.0 <= value <= 1.0 for value in resource)
    assert NETWORK_PARAMETER_COUNT_V1 == 71_172


def test_reward_and_epsilon_contract() -> None:
    assert reward_from_merge_score_v1(0) == 0.0
    assert reward_from_merge_score_v1(2048) == 1.0
    assert epsilon_at_interaction_v1(0, decay_steps=100) == 1.0
    assert epsilon_at_interaction_v1(100, decay_steps=100) == pytest.approx(0.05)
    assert epsilon_at_interaction_v1(1000, decay_steps=100) == pytest.approx(0.05)


def test_unregistered_arm_is_rejected() -> None:
    state = initial_state_v1(seed="unit", episode_index=0)
    with pytest.raises(MatchedDoubleDQN2048V1Error, match="not registered"):
        observation_vector_v1(state, "RAW_PLUS_RESOURCE")


def test_tiny_cpu_loop_materializes_separate_compute_and_sample_axes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pytest.importorskip("numpy")
    pytest.importorskip("torch")
    protocol = build_pilot_protocol_v1()
    training = protocol["training"]
    training.update(
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
    training["epsilon_schedule"]["decay_steps"] = 20
    monkeypatch.setattr(runtime, "build_pilot_protocol_v1", lambda: protocol)

    result, _ = run_pilot_seed_arm_v1(
        arm="RESOURCE_STATE_ONLY", seed=41001, device_name="cpu"
    )

    ledger = SampleLedgerV1.from_document(result["sample_ledger"])
    assert ledger.evidence_count(
        EvidenceClass.ENVIRONMENT_INTERACTION, EvidenceLane.ONLINE_TARGET
    ) == 20
    assert ledger.evidence_count(
        EvidenceClass.EXACT_KERNEL_QUERY, EvidenceLane.ONLINE_TARGET
    ) == 40
    assert ledger.evidence_count(
        EvidenceClass.EXACT_KERNEL_QUERY, EvidenceLane.STANDALONE_EVALUATION
    ) == result["decision_latency_telemetry"]["decision_count"]
    compute = result["compute_telemetry"]
    assert compute["training_wall_time_excluding_standalone_evaluation_ns"] > 0
    assert compute["standalone_evaluation_wall_time_ns"] > 0
    assert compute["training_decision_encoding_calls"] == 20
    assert compute["replay_next_encoding_calls"] == 20
    assert compute["optimizer_update_calls"] == 5
    assert result["evaluations"][0]["compute_telemetry"][
        "policy_forward_calls"
    ] > 0
