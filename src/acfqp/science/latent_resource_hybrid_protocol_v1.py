"""Outcome-free pilot protocol for raw-preserving resource augmentation.

The u003 confirmatory result showed a large early-learning advantage for the
state-only resource vector but heterogeneous final outcomes after the raw
board had been discarded.  This successor therefore asks a narrower question:
does the same deterministic resource vector add useful inductive bias when the
lossless raw board remains present?

Both pilot arms expose 32 active inputs and use the same network.  The control
concatenates the normalized board with a fixed 180-degree rotation of itself;
the candidate concatenates the board with the state-only resource vector.
The rotated copy is a deterministic bijection of already available data, so it
matches width and active first-layer inputs without adding information.
"""

from __future__ import annotations

import hashlib
from typing import Any

from acfqp.phase3e_ids import canonical_json_bytes


HYBRID_PROTOCOL_DOMAIN = "acfqp:latent-resource-hybrid-pilot-protocol:v1"
HYBRID_PILOT_ARMS = (
    "RAW_PLUS_ROTATED_RAW_CONTROL",
    "RAW_PLUS_RESOURCE_STATE_ONLY",
)
HYBRID_INPUT_DIMENSION_V1 = 32
HYBRID_PILOT_TRAINING_SEEDS_V1 = (740101, 740102)


def _training_contract_v1() -> dict[str, Any]:
    return {
        "environment_steps_per_seed_arm": 100_000,
        "evaluation_checkpoints": [25_000, 50_000, 100_000],
        "evaluation_episodes_per_checkpoint": 32,
        "replay_capacity": 250_000,
        "replay_warmup_environment_steps": 10_000,
        "batch_size": 256,
        "train_every_environment_steps": 4,
        "gradient_updates_per_train_event": 1,
        "target_network_sync_environment_steps": 2_000,
        "discount": {"numerator": 99, "denominator": 100},
        "adam_learning_rate": {"numerator": 3, "denominator": 10_000},
        "huber_delta": 1,
        "epsilon_schedule": {
            "kind": "LINEAR_BY_ONLINE_TARGET_ENVIRONMENT_INTERACTION",
            "start": {"numerator": 1, "denominator": 1},
            "end": {"numerator": 1, "denominator": 20},
            "decay_steps": 100_000,
        },
        "reward_transform": "log2(merge_score)/11_if_positive_else_zero",
        "episode_ends_on": ["WON_AT_TILE_2048", "NO_LEGAL_ACTION"],
        "training_evaluation_separation": True,
    }


def build_hybrid_pilot_protocol_v1() -> dict[str, Any]:
    """Return the fixed nonconfirmatory calibration protocol."""

    payload: dict[str, Any] = {
        "schema": "acfqp.science.latent_resource_hybrid_pilot_protocol.v1",
        "campaign_kind": "HYBRID_PILOT_NONCONFIRMATORY",
        "research_question": (
            "Does a deterministic state-only resource vector improve matched "
            "Double-DQN when the lossless raw 2048 board is retained?"
        ),
        "predecessor_protocol_id": (
            "8b77cfe4f3549f7f6ba6e586a8fca41aefa29feb0d03ab8aa27ab694f7e98b3e"
        ),
        "predecessor_joint_gate": "FAIL_RETAINED_WITHOUT_REINTERPRETATION",
        "arms": list(HYBRID_PILOT_ARMS),
        "training_seeds": list(HYBRID_PILOT_TRAINING_SEEDS_V1),
        "training_tape_prefix": "acfqp-latent-resource-hybrid-pilot-train-v1",
        "evaluation_tape_prefix": "acfqp-latent-resource-hybrid-pilot-eval-v1",
        "representation_contract": {
            "input_dimension_for_every_arm": HYBRID_INPUT_DIMENSION_V1,
            "first_block": "sixteen normalized lossless board ranks",
            "control_second_block": (
                "the same normalized board under one fixed 180-degree rotation"
            ),
            "candidate_second_block": (
                "the frozen sixteen-coordinate state-only resource adapter"
            ),
            "control_second_block_adds_no_information": True,
            "candidate_is_deterministic_from_the_same_current_board": True,
            "candidate_calls_no_transition_or_successor_kernel": True,
            "both_second_blocks_are_active_not_zero_padding": True,
        },
        "network_contract": {
            "algorithm": "DOUBLE_DQN",
            "mlp_hidden_widths": [256, 256],
            "activation": "RELU",
            "output_action_count": 4,
            "same_parameter_count_for_both_arms": True,
            "same_optimizer_replay_target_update_epsilon_reward_and_budget": True,
        },
        "sample_ledger_contract": {
            "primary_sample_tax_axis": "online_target.ENVIRONMENT_INTERACTION",
            "all_twenty_rows_materialized_including_native_zero": True,
            "representation_adds_zero_exact_kernel_queries": True,
        },
        "training": _training_contract_v1(),
        "statistics_gate": "NOT_RUN_PILOT",
        "scientific_success_claimed": False,
        "pilot_outcomes_may_design_a_fresh_successor_but_cannot_change_u003": True,
    }
    protocol_id = hashlib.sha256(
        HYBRID_PROTOCOL_DOMAIN.encode("ascii")
        + b"\x00"
        + canonical_json_bytes(payload)
    ).hexdigest()
    return {**payload, "protocol_id": protocol_id}


__all__ = (
    "HYBRID_INPUT_DIMENSION_V1",
    "HYBRID_PILOT_ARMS",
    "HYBRID_PILOT_TRAINING_SEEDS_V1",
    "build_hybrid_pilot_protocol_v1",
)
