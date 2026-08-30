from __future__ import annotations

import pytest

from acfqp.science.latent_resource_hybrid_protocol_v1 import (
    HYBRID_INPUT_DIMENSION_V1,
    HYBRID_PILOT_ARMS,
    build_hybrid_pilot_protocol_v1,
)
from acfqp.science.matched_2048_env_v1 import initial_state_v1
from acfqp.science import matched_double_dqn_2048_hybrid_v1 as runtime
from acfqp.science.matched_double_dqn_2048_hybrid_v1 import (
    HYBRID_NETWORK_PARAMETER_COUNT_V1,
    HYBRID_PILOT_RESULT_SCHEMA_V1,
    observation_vector_hybrid_v1,
    run_hybrid_pilot_seed_arm_v1,
)
from acfqp.science.matched_double_dqn_2048_v1 import (
    MatchedDoubleDQN2048V1Error,
    observation_vector_v1,
)
from acfqp.science.sample_ledger_v1 import EvidenceClass, EvidenceLane, SampleLedgerV1


def test_hybrid_protocol_and_observations_are_matched_and_outcome_free() -> None:
    protocol = build_hybrid_pilot_protocol_v1()
    replay = build_hybrid_pilot_protocol_v1()
    state = initial_state_v1(seed="hybrid-unit", episode_index=0)
    raw = observation_vector_v1(state, "RAW_BOARD")
    resource = observation_vector_v1(state, "RESOURCE_STATE_ONLY")
    control = observation_vector_hybrid_v1(
        state, "RAW_PLUS_ROTATED_RAW_CONTROL"
    )
    candidate = observation_vector_hybrid_v1(
        state, "RAW_PLUS_RESOURCE_STATE_ONLY"
    )

    assert protocol == replay
    assert protocol["arms"] == list(HYBRID_PILOT_ARMS)
    assert protocol["statistics_gate"] == "NOT_RUN_PILOT"
    assert protocol["scientific_success_claimed"] is False
    assert len(control) == len(candidate) == HYBRID_INPUT_DIMENSION_V1 == 32
    assert control[:16] == candidate[:16] == raw
    assert control[16:] == tuple(reversed(raw))
    assert candidate[16:] == resource
    assert all(0.0 <= value <= 1.0 for value in control + candidate)


def test_hybrid_rejects_unregistered_arm() -> None:
    state = initial_state_v1(seed="hybrid-unit", episode_index=0)
    with pytest.raises(MatchedDoubleDQN2048V1Error, match="not registered"):
        observation_vector_hybrid_v1(state, "RAW_BOARD")


def test_tiny_hybrid_cpu_loop_keeps_network_and_sample_axes_matched(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pytest.importorskip("numpy")
    pytest.importorskip("torch")
    protocol = build_hybrid_pilot_protocol_v1()
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
    monkeypatch.setattr(runtime, "build_hybrid_pilot_protocol_v1", lambda: protocol)

    results = []
    for arm in HYBRID_PILOT_ARMS:
        result, _ = run_hybrid_pilot_seed_arm_v1(
            arm=arm, seed=740101, device_name="cpu"
        )
        results.append(result)
        ledger = SampleLedgerV1.from_document(result["sample_ledger"])
        assert ledger.evidence_count(
            EvidenceClass.ENVIRONMENT_INTERACTION, EvidenceLane.ONLINE_TARGET
        ) == 20
        assert ledger.evidence_count(
            EvidenceClass.EXACT_KERNEL_QUERY, EvidenceLane.ONLINE_TARGET
        ) == 40
        telemetry = result["representation_telemetry"]
        assert result["schema"] == HYBRID_PILOT_RESULT_SCHEMA_V1
        assert result["network_parameter_count"] == HYBRID_NETWORK_PARAMETER_COUNT_V1
        assert result["training_environment_interactions"] == 20
        assert result["pilot_scientific_gate"] == "NOT_RUN"
        assert result["scientific_success_claimed"] is False
        assert telemetry["input_dimension"] == 32
        assert telemetry["lossless_raw_board_retained"] is True
        assert telemetry["arm_observation_bytes"] == 128
        assert result["decision_latency_telemetry"][
            "includes_hybrid_observation_encoding_action_mask_and_policy_forward"
        ] is True

    assert {result["network_parameter_count"] for result in results} == {
        HYBRID_NETWORK_PARAMETER_COUNT_V1
    }
    assert HYBRID_NETWORK_PARAMETER_COUNT_V1 == 75_268
