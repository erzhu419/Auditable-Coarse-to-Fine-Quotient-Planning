"""Matched 32-D pilot for raw-preserving latent-resource augmentation."""

from __future__ import annotations

import math
from typing import Any

from acfqp.domains import standard_2048
from acfqp.science.latent_resource_2048_v1 import (
    encode_standard_2048_state_only_state_v1,
)
from acfqp.science.latent_resource_hybrid_protocol_v1 import (
    HYBRID_INPUT_DIMENSION_V1,
    HYBRID_PILOT_ARMS,
    build_hybrid_pilot_protocol_v1,
)
from acfqp.science.matched_double_dqn_2048_v1 import (
    MatchedDoubleDQN2048V1Error,
    _run_seed_arm_v1,
)


HYBRID_PILOT_RESULT_SCHEMA_V1 = (
    "acfqp.science.matched_double_dqn_2048_hybrid_pilot_result.v1"
)
HYBRID_NETWORK_PARAMETER_COUNT_V1 = 75_268


def _validate_state_v1(state: Any) -> None:
    if type(state) is not standard_2048.Swipe2048State:
        raise MatchedDoubleDQN2048V1Error(
            "hybrid observation requires one exact standard 2048 state"
        )
    standard_2048.validate_board_v1(state.board)
    if state != standard_2048.state_from_board_v1(state.board):
        raise MatchedDoubleDQN2048V1Error(
            "hybrid observation state status disagrees with its board"
        )


def observation_vector_hybrid_v1(state: Any, arm: str) -> tuple[float, ...]:
    """Return one matched 32-D control or raw-plus-resource observation."""

    if arm not in HYBRID_PILOT_ARMS:
        raise MatchedDoubleDQN2048V1Error("hybrid arm is not registered")
    _validate_state_v1(state)
    raw = tuple(
        min(rank, standard_2048.GOAL_RANK) / standard_2048.GOAL_RANK
        for rank in state.board
    )
    if arm == "RAW_PLUS_ROTATED_RAW_CONTROL":
        second = tuple(reversed(raw))
    else:
        second = tuple(
            float(value)
            for value in encode_standard_2048_state_only_state_v1(
                state
            ).resource_vector
        )
    observation = raw + second
    if (
        len(observation) != HYBRID_INPUT_DIMENSION_V1
        or any(not math.isfinite(value) for value in observation)
        or any(not 0.0 <= value <= 1.0 for value in observation)
    ):
        raise MatchedDoubleDQN2048V1Error("hybrid network observation changed")
    return observation


def _representation_telemetry_v1(
    arm: str, raw_signature_count: int, active_signature_count: int
) -> dict[str, Any]:
    return {
        "active_representation": arm,
        "executed_arm": arm,
        "input_dimension": HYBRID_INPUT_DIMENSION_V1,
        "raw_observation_bytes": 64,
        "arm_observation_bytes": HYBRID_INPUT_DIMENSION_V1 * 4,
        "lossless_raw_board_retained": True,
        "lossless_raw_board_signature_count": raw_signature_count,
        "quantized_active_observation_signature_count": active_signature_count,
        "active_observation_quantization_bins_per_coordinate": 256,
        "second_block_kind": (
            "FIXED_180_DEGREE_RAW_REDUNDANCY"
            if arm == "RAW_PLUS_ROTATED_RAW_CONTROL"
            else "STATE_ONLY_LATENT_RESOURCE"
        ),
        "second_block_is_deterministic_from_current_board": True,
        "second_block_calls_no_transition_or_successor_kernel": True,
        "control_second_block_is_bijective_redundancy": (
            arm == "RAW_PLUS_ROTATED_RAW_CONTROL"
        ),
        "candidate_second_block_is_human_inductive_bias": (
            arm == "RAW_PLUS_RESOURCE_STATE_ONLY"
        ),
        "compression_claimed": False,
    }


def run_hybrid_pilot_seed_arm_v1(
    *, arm: str, seed: int, device_name: str = "cuda:0"
) -> tuple[dict[str, Any], Any]:
    """Run one registered nonconfirmatory hybrid-pilot seed-arm."""

    protocol = build_hybrid_pilot_protocol_v1()
    return _run_seed_arm_v1(
        protocol=protocol,
        arm=arm,
        seed=seed,
        device_name=device_name,
        result_schema=HYBRID_PILOT_RESULT_SCHEMA_V1,
        training_tape_prefix=protocol["training_tape_prefix"],
        result_gate_fields={
            "pilot_scientific_gate": "NOT_RUN",
            "predecessor_u003_joint_gate": "FAIL",
            "scientific_success_claimed": False,
        },
        observation_builder=observation_vector_hybrid_v1,
        input_dimension=HYBRID_INPUT_DIMENSION_V1,
        expected_parameter_count=HYBRID_NETWORK_PARAMETER_COUNT_V1,
        collect_both_signature_families=True,
        representation_telemetry_builder=_representation_telemetry_v1,
        decision_latency_scope_field=(
            "includes_hybrid_observation_encoding_action_mask_and_policy_forward"
        ),
    )


__all__ = (
    "HYBRID_NETWORK_PARAMETER_COUNT_V1",
    "HYBRID_PILOT_ARMS",
    "HYBRID_PILOT_RESULT_SCHEMA_V1",
    "observation_vector_hybrid_v1",
    "run_hybrid_pilot_seed_arm_v1",
)
