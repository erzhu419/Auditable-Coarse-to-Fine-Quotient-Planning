"""Fresh matched policy training for the learned resource-forecast pilot.

The three generator arms retain the u005 Double-DQN observations and training
contract.  Unlike u005, this runtime retains the inference-only online network
at every registered checkpoint because each snapshot is one downstream player
identity.  It deliberately does not return or save a second final-model
artifact.
"""

from __future__ import annotations

from collections import OrderedDict
from typing import Any, Mapping

from acfqp.science.latent_resource_hybrid_confirmatory_protocol_v2 import (
    HYBRID_INPUT_DIMENSION_V2,
    HYBRID_PARAMETER_COUNT_V2,
    RAW_STANDARD_INPUT_DIMENSION_V2,
    RAW_STANDARD_PARAMETER_COUNT_V2,
)
from acfqp.science.learned_resource_forecast_protocol_v1 import (
    LEARNED_RESOURCE_FORECAST_ARMS_V1,
    validate_ratified_learned_resource_forecast_protocol_v1,
)
from acfqp.science.matched_double_dqn_2048_hybrid_confirmatory_v2 import (
    observation_vector_hybrid_confirmatory_v2,
)
from acfqp.science.matched_double_dqn_2048_v1 import (
    MatchedDoubleDQN2048V1Error,
    _run_seed_arm_v1,
)


LEARNED_RESOURCE_POLICY_TRAINING_RESULT_SCHEMA_V1 = (
    "acfqp.science.learned_resource_forecast_policy_training_seed_arm_result.v1"
)
RAW_STANDARD_ARM_V1 = LEARNED_RESOURCE_FORECAST_ARMS_V1[0]
ROTATED_CONTROL_ARM_V1 = LEARNED_RESOURCE_FORECAST_ARMS_V1[1]
RESOURCE_CANDIDATE_ARM_V1 = LEARNED_RESOURCE_FORECAST_ARMS_V1[2]


def expected_policy_training_execution_id_v1(
    protocol: Mapping[str, Any], *, arm: str, seed: int
) -> str:
    """Return the sole registered execution identity for one seed-arm job."""

    if (
        type(protocol) is not dict
        or arm not in protocol.get("arms", ())
        or seed not in protocol.get("training_seeds", ())
        or type(protocol.get("pilot_execution_identity")) is not str
        or not protocol["pilot_execution_identity"]
    ):
        raise MatchedDoubleDQN2048V1Error(
            "learned resource policy seed-arm identity is not registered"
        )
    return (
        f"{protocol['pilot_execution_identity']}:policy-training:"
        f"{arm}:seed:{seed}"
    )


def policy_checkpoint_filename_v1(
    *, arm: str, seed: int, checkpoint: int
) -> str:
    """Return the stable basename for one inference-only online snapshot."""

    if (
        arm not in LEARNED_RESOURCE_FORECAST_ARMS_V1
        or type(seed) is not int
        or type(checkpoint) is not int
        or checkpoint <= 0
    ):
        raise MatchedDoubleDQN2048V1Error(
            "learned resource policy checkpoint identity changed"
        )
    return (
        f"{arm.lower()}-seed-{seed}-checkpoint-{checkpoint}.pt"
    )


def _representation_telemetry_v1(
    arm: str, raw_signature_count: int, active_signature_count: int
) -> dict[str, Any]:
    if arm == RAW_STANDARD_ARM_V1:
        input_dimension = RAW_STANDARD_INPUT_DIMENSION_V2
        second_block_kind = "NONE_RAW_STANDARD"
    elif arm == ROTATED_CONTROL_ARM_V1:
        input_dimension = HYBRID_INPUT_DIMENSION_V2
        second_block_kind = "FIXED_180_DEGREE_RAW_REDUNDANCY"
    elif arm == RESOURCE_CANDIDATE_ARM_V1:
        input_dimension = HYBRID_INPUT_DIMENSION_V2
        second_block_kind = "STATE_ONLY_LATENT_RESOURCE"
    else:  # pragma: no cover - the validated protocol rejects this first
        raise MatchedDoubleDQN2048V1Error(
            "learned resource policy arm is not registered"
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
            arm == ROTATED_CONTROL_ARM_V1
        ),
        "candidate_second_block_is_human_inductive_bias": (
            arm == RESOURCE_CANDIDATE_ARM_V1
        ),
        "parameter_count_equal_to_rotated_control": (
            arm in (ROTATED_CONTROL_ARM_V1, RESOURCE_CANDIDATE_ARM_V1)
        ),
        "parameter_count_equal_to_raw_standard": arm == RAW_STANDARD_ARM_V1,
        "compression_claimed": False,
    }


def run_learned_resource_policy_training_seed_arm_v1(
    *,
    protocol: Mapping[str, Any],
    arm: str,
    seed: int,
    device_name: str = "cuda:0",
) -> tuple[dict[str, Any], dict[int, OrderedDict[str, Any]]]:
    """Train one fresh generator policy and copy every registered checkpoint.

    Snapshot values are cloned onto CPU when the callback fires.  Therefore a
    later optimizer update cannot mutate an earlier checkpoint, and the caller
    can serialize each returned value directly as a bare Torch ``state_dict``.
    """

    validated = validate_ratified_learned_resource_forecast_protocol_v1(protocol)
    if arm == RAW_STANDARD_ARM_V1:
        input_dimension = RAW_STANDARD_INPUT_DIMENSION_V2
        parameter_count = RAW_STANDARD_PARAMETER_COUNT_V2
    else:
        input_dimension = HYBRID_INPUT_DIMENSION_V2
        parameter_count = HYBRID_PARAMETER_COUNT_V2

    snapshots: dict[int, OrderedDict[str, Any]] = {}

    def capture_checkpoint(interaction: int, online: Any) -> None:
        if interaction in snapshots:
            raise MatchedDoubleDQN2048V1Error(
                "learned resource policy checkpoint was observed twice"
            )
        snapshots[interaction] = OrderedDict(
            (name, value.detach().cpu().clone())
            for name, value in online.state_dict().items()
        )

    result, _final_online = _run_seed_arm_v1(
        protocol=validated,
        arm=arm,
        seed=seed,
        device_name=device_name,
        result_schema=LEARNED_RESOURCE_POLICY_TRAINING_RESULT_SCHEMA_V1,
        training_tape_prefix=validated["training_tape_prefix"],
        result_gate_fields={
            "policy_training_matrix_gate": (
                "NOT_RUN_REQUIRES_COMPLETE_144_JOB_432_SNAPSHOT_MATRIX"
            ),
            "tape_binding": {
                "training_tape_root": (
                    f"{validated['training_tape_prefix']}:{seed}"
                ),
                "model_evaluation_tape_root": validated[
                    "evaluation_tape_prefix"
                ],
                "same_seed_training_tape_across_generator_arms": True,
                "same_model_evaluation_tape_across_all_seed_arms": True,
            },
            "checkpoint_artifact_contract": {
                "kind": "INFERENCE_ONLY_BARE_ONLINE_STATE_DICT",
                "registered_checkpoints": list(
                    validated["training"]["evaluation_checkpoints"]
                ),
                "separate_final_model_artifact_written": False,
            },
            "scientific_success_claimed": False,
        },
        observation_builder=observation_vector_hybrid_confirmatory_v2,
        input_dimension=input_dimension,
        expected_parameter_count=parameter_count,
        collect_both_signature_families=True,
        representation_telemetry_builder=_representation_telemetry_v1,
        checkpoint_observer=capture_checkpoint,
        decision_latency_scope_field=(
            "includes_raw_or_hybrid_observation_action_mask_and_policy_forward"
        ),
    )
    expected_checkpoints = tuple(
        validated["training"]["evaluation_checkpoints"]
    )
    if tuple(snapshots) != expected_checkpoints:
        raise MatchedDoubleDQN2048V1Error(
            "learned resource policy checkpoint callback did not close its roster"
        )
    return result, snapshots


__all__ = (
    "LEARNED_RESOURCE_POLICY_TRAINING_RESULT_SCHEMA_V1",
    "RAW_STANDARD_ARM_V1",
    "RESOURCE_CANDIDATE_ARM_V1",
    "ROTATED_CONTROL_ARM_V1",
    "expected_policy_training_execution_id_v1",
    "policy_checkpoint_filename_v1",
    "run_learned_resource_policy_training_seed_arm_v1",
)
