"""Runtime for the fresh raw-preserving hybrid confirmatory matrix."""

from __future__ import annotations

from typing import Any, Mapping

from acfqp.science.latent_resource_hybrid_confirmatory_protocol_v2 import (
    HYBRID_CONFIRMATORY_ARMS_V2,
    HYBRID_INPUT_DIMENSION_V2,
    HYBRID_PARAMETER_COUNT_V2,
    RAW_STANDARD_ARM_V2,
    RAW_STANDARD_INPUT_DIMENSION_V2,
    RAW_STANDARD_PARAMETER_COUNT_V2,
    RESOURCE_CANDIDATE_ARM_V2,
    ROTATED_CONTROL_ARM_V2,
    validate_ratified_hybrid_confirmatory_protocol_v2,
)
from acfqp.science.matched_double_dqn_2048_hybrid_v1 import (
    observation_vector_hybrid_v1,
)
from acfqp.science.matched_double_dqn_2048_v1 import (
    MatchedDoubleDQN2048V1Error,
    _run_seed_arm_v1,
    observation_vector_v1,
)


HYBRID_CONFIRMATORY_RESULT_SCHEMA_V2 = (
    "acfqp.science.matched_double_dqn_2048_hybrid_confirmatory_seed_arm_result.v2"
)


def observation_vector_hybrid_confirmatory_v2(
    state: Any, arm: str
) -> tuple[float, ...]:
    """Return the registered 16-D baseline or one registered 32-D hybrid."""

    if arm == RAW_STANDARD_ARM_V2:
        return observation_vector_v1(state, "RAW_BOARD")
    if arm in (ROTATED_CONTROL_ARM_V2, RESOURCE_CANDIDATE_ARM_V2):
        return observation_vector_hybrid_v1(state, arm)
    raise MatchedDoubleDQN2048V1Error(
        "hybrid confirmatory arm is not registered"
    )


def _representation_telemetry_v2(
    arm: str, raw_signature_count: int, active_signature_count: int
) -> dict[str, Any]:
    if arm == RAW_STANDARD_ARM_V2:
        input_dimension = RAW_STANDARD_INPUT_DIMENSION_V2
        second_block_kind = "NONE_RAW_STANDARD"
    elif arm == ROTATED_CONTROL_ARM_V2:
        input_dimension = HYBRID_INPUT_DIMENSION_V2
        second_block_kind = "FIXED_180_DEGREE_RAW_REDUNDANCY"
    elif arm == RESOURCE_CANDIDATE_ARM_V2:
        input_dimension = HYBRID_INPUT_DIMENSION_V2
        second_block_kind = "STATE_ONLY_LATENT_RESOURCE"
    else:  # pragma: no cover - _run_seed_arm_v1 checks the arm first
        raise MatchedDoubleDQN2048V1Error(
            "hybrid confirmatory telemetry arm is not registered"
        )
    return {
        "active_representation": arm,
        "executed_arm": arm,
        "input_dimension": input_dimension,
        "raw_observation_bytes": 64,
        "arm_observation_bytes": input_dimension * 4,
        "lossless_raw_board_retained": True,
        "lossless_raw_board_signature_count": raw_signature_count,
        "quantized_active_observation_signature_count": active_signature_count,
        "active_observation_quantization_bins_per_coordinate": 256,
        "second_block_kind": second_block_kind,
        "second_block_is_deterministic_from_current_board": True,
        "second_block_calls_transition_or_successor_kernel": False,
        "control_second_block_is_bijective_redundancy": (
            arm == ROTATED_CONTROL_ARM_V2
        ),
        "candidate_second_block_is_human_inductive_bias": (
            arm == RESOURCE_CANDIDATE_ARM_V2
        ),
        "parameter_count_equal_to_rotated_control": (
            arm in (ROTATED_CONTROL_ARM_V2, RESOURCE_CANDIDATE_ARM_V2)
        ),
        "parameter_count_equal_to_raw_standard": arm == RAW_STANDARD_ARM_V2,
        "compression_claimed": False,
    }


def run_hybrid_confirmatory_seed_arm_v2(
    *,
    protocol: Mapping[str, Any],
    arm: str,
    seed: int,
    device_name: str = "cuda:0",
) -> tuple[dict[str, Any], Any]:
    """Run one seed-arm from the exactly ratified 72-job u005 matrix."""

    validated = validate_ratified_hybrid_confirmatory_protocol_v2(protocol)
    if arm == RAW_STANDARD_ARM_V2:
        input_dimension = RAW_STANDARD_INPUT_DIMENSION_V2
        parameter_count = RAW_STANDARD_PARAMETER_COUNT_V2
    else:
        input_dimension = HYBRID_INPUT_DIMENSION_V2
        parameter_count = HYBRID_PARAMETER_COUNT_V2
    return _run_seed_arm_v1(
        protocol=validated,
        arm=arm,
        seed=seed,
        device_name=device_name,
        result_schema=HYBRID_CONFIRMATORY_RESULT_SCHEMA_V2,
        training_tape_prefix=validated["training_tape_prefix"],
        result_gate_fields={
            "hybrid_confirmatory_joint_gate": (
                "NOT_RUN_REQUIRES_COMPLETE_72_ARTIFACT_MATRIX"
            ),
            "tape_binding": {
                "training_tape_root": (
                    f"{validated['training_tape_prefix']}:{seed}"
                ),
                "evaluation_tape_root": validated["evaluation_tape_prefix"],
                "same_seed_training_tape_across_arms": True,
                "same_evaluation_tapes_across_all_seed_arms": True,
            },
            "scientific_success_claimed": False,
        },
        observation_builder=observation_vector_hybrid_confirmatory_v2,
        input_dimension=input_dimension,
        expected_parameter_count=parameter_count,
        collect_both_signature_families=True,
        representation_telemetry_builder=_representation_telemetry_v2,
        decision_latency_scope_field=(
            "includes_raw_or_hybrid_observation_action_mask_and_policy_forward"
        ),
    )


__all__ = (
    "HYBRID_CONFIRMATORY_ARMS_V2",
    "HYBRID_CONFIRMATORY_RESULT_SCHEMA_V2",
    "observation_vector_hybrid_confirmatory_v2",
    "run_hybrid_confirmatory_seed_arm_v2",
)
