"""Outcome-free protocol for the learned resource-forecast 2048 U002 pilot.

U002 is the fresh ordinal-2, attempt-1 successor of the new exploratory method
family.  U001 is immutable prior execution evidence, and the two failed
hand-designed short-signature pilots are design history only.  None of their
identities, policies, labels, tapes, features, or outcomes is eligible for this
pilot's Gate.
"""

from __future__ import annotations

import hashlib
import re
from typing import Any, Mapping, NoReturn

from acfqp.phase3e_ids import canonical_json_bytes


LEARNED_RESOURCE_FORECAST_PROTOCOL_DOMAIN_V1 = (
    "acfqp:learned-resource-forecast-2048-pilot-protocol:v1"
)
LEARNED_RESOURCE_FORECAST_PROTOCOL_SCHEMA_V1 = (
    "acfqp.science.learned_resource_forecast_2048_pilot_protocol.v1"
)
LEARNED_RESOURCE_FORECAST_EXECUTION_IDENTITY_V1 = (
    "acfqp-learned-resource-forecast-2048-pilot-u002-ordinal2-attempt1"
)
LEARNED_RESOURCE_FORECAST_PREDECESSOR_EXECUTION_IDENTITY_V1 = (
    "acfqp-learned-resource-forecast-2048-pilot-u001-ordinal1-attempt1"
)

# These are policy-generator arms.  They are identities, never classifier
# coordinates.
LEARNED_RESOURCE_FORECAST_ARMS_V1 = (
    "RAW_BOARD_STANDARD",
    "RAW_PLUS_ROTATED_RAW_CONTROL",
    "RAW_PLUS_RESOURCE_STATE_ONLY",
)
LEARNED_RESOURCE_FORECAST_TRAINING_SEEDS_V1 = tuple(range(782_101, 782_149))
LEARNED_RESOURCE_FORECAST_TRAIN_SEEDS_V1 = (
    LEARNED_RESOURCE_FORECAST_TRAINING_SEEDS_V1[:32]
)
LEARNED_RESOURCE_FORECAST_TEST_SEEDS_V1 = (
    LEARNED_RESOURCE_FORECAST_TRAINING_SEEDS_V1[32:]
)
LEARNED_RESOURCE_FORECAST_CHECKPOINTS_V1 = (25_000, 50_000, 100_000)

# These are downstream representations.  They are deliberately distinct from
# the policy-generator arm registry above.
RAW_PREFIX_ARM_V1 = "RAW_PREFIX"
SHUFFLED_FORECAST_ARM_V1 = "RAW_PLUS_PLAYER_SHUFFLED_FORECAST"
ALIGNED_FORECAST_ARM_V1 = "RAW_PLUS_ALIGNED_RESOURCE_FORECAST"
PROBE_REPRESENTATION_ARMS_V1 = (
    RAW_PREFIX_ARM_V1,
    SHUFFLED_FORECAST_ARM_V1,
    ALIGNED_FORECAST_ARM_V1,
)
RAW_PREFIX_DIMENSION_V1 = 184
LEARNED_PREFIX_DIMENSION_V1 = 248
PROBE_REPRESENTATION_DIMENSIONS_V1 = {
    RAW_PREFIX_ARM_V1: RAW_PREFIX_DIMENSION_V1,
    SHUFFLED_FORECAST_ARM_V1: LEARNED_PREFIX_DIMENSION_V1,
    ALIGNED_FORECAST_ARM_V1: LEARNED_PREFIX_DIMENSION_V1,
}

TRAINING_TAPE_PREFIX_V1 = (
    "acfqp-learned-resource-forecast-u002-policy-training-v1"
)
MODEL_EVALUATION_TAPE_PREFIX_V1 = (
    "acfqp-learned-resource-forecast-u002-model-evaluation-v1"
)
TRAJECTORY_TAPE_ROOT_V1 = (
    "acfqp-learned-resource-forecast-u002-self-supervised-trajectory-v1"
)
LABEL_TAPE_ROOT_V1 = "acfqp-learned-resource-forecast-u002-skill-label-v1"
PROBE_TAPE_ROOT_V1 = "acfqp-learned-resource-forecast-u002-eight-action-probe-v1"

TRAJECTORY_EPISODES_PER_TRAIN_PLAYER_V1 = 16
LABEL_EPISODES_PER_PLAYER_V1 = 64
PROBES_PER_PLAYER_V1 = 16
MAX_WINDOWS_PER_TRAJECTORY_EPISODE_V1 = 32
PREFIX_ACTION_COUNT_V1 = 8
GRU_INPUT_WIDTH_V1 = 21
GRU_HIDDEN_WIDTH_V1 = 64
FORECAST_TARGET_WIDTH_V1 = 54
FORECAST_EPOCHS_V1 = 50
FORECAST_BATCH_SIZE_V1 = 256
LOGISTIC_L2_STRENGTH_V1 = 1.0
BOOTSTRAP_REPLICATES_V1 = 20_000
BOOTSTRAP_RANDOM_SEED_V1 = 881_003
ENCODER_INITIALIZATION_SEED_V1 = 881_001
TARGET_SHUFFLE_SEED_V1 = 881_002

EXPECTED_TRAINING_JOB_COUNT_V1 = 144
EXPECTED_MODEL_SNAPSHOT_COUNT_V1 = 432
EXPECTED_PLAYER_COUNT_V1 = 432
EXPECTED_PROBE_RECORD_COUNT_V1 = 6_912
EXPECTED_TRAJECTORY_PLAYER_ARTIFACT_COUNT_V1 = 288
EXPECTED_COMPLETE_TRAJECTORY_EPISODE_COUNT_V1 = 4_608
EXPECTED_FORECAST_ENCODER_RECEIPT_COUNT_V1 = 2
EXPECTED_FROZEN_ENCODER_STATE_COUNT_V1 = 2

FAILED_NATURAL_OPENING_PROTOCOL_ID_V1 = (
    "d06e07f8f49ac4ef9957417befe766cd411ee928e574724199c849d4e8b5b6ee"
)
FAILED_DECISION_POINT_PROTOCOL_ID_V1 = (
    "183e1b1a6812792a22e1e58a103422e5dde5a91a5c1a72af8e654fdb48272e91"
)


class LearnedResourceForecastProtocolV1Error(ValueError):
    """The frozen U002 design or content identity changed."""


def _fail(message: str) -> NoReturn:
    raise LearnedResourceForecastProtocolV1Error(message)


def _with_identity_v1(payload: dict[str, Any]) -> dict[str, Any]:
    protocol_id = hashlib.sha256(
        LEARNED_RESOURCE_FORECAST_PROTOCOL_DOMAIN_V1.encode("ascii")
        + b"\x00"
        + canonical_json_bytes(payload)
    ).hexdigest()
    return {**payload, "protocol_id": protocol_id}


def _training_contract_v1() -> dict[str, Any]:
    """Return the unchanged matched Double-DQN training contract."""

    return {
        "environment_steps_per_seed_arm": 100_000,
        "evaluation_checkpoints": list(LEARNED_RESOURCE_FORECAST_CHECKPOINTS_V1),
        "evaluation_episodes_per_checkpoint": 64,
        "save_inference_only_online_network_at_each_checkpoint": True,
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
        "algorithm_and_schedule_unchanged_from_u005": True,
    }


def _frozen_payload_v1() -> dict[str, Any]:
    tape_roots = (
        TRAINING_TAPE_PREFIX_V1,
        MODEL_EVALUATION_TAPE_PREFIX_V1,
        TRAJECTORY_TAPE_ROOT_V1,
        LABEL_TAPE_ROOT_V1,
        PROBE_TAPE_ROOT_V1,
    )
    if len(set(tape_roots)) != 5:
        raise AssertionError("U002 tape roots must be pairwise distinct")
    return {
        "schema": LEARNED_RESOURCE_FORECAST_PROTOCOL_SCHEMA_V1,
        "schema_version": "1.0.0",
        "campaign_kind": "LEARNED_RESOURCE_FORECAST_2048_PILOT_U002_TEMPLATE",
        "research_question": (
            "Can a label-free representation learned from complete goal-terminated "
            "2048 trajectories add held-out predictive utility to exactly eight "
            "accepted opening actions?"
        ),
        "source_commit": None,
        "pilot_execution_identity": None,
        "arms": list(LEARNED_RESOURCE_FORECAST_ARMS_V1),
        "training_seeds": list(LEARNED_RESOURCE_FORECAST_TRAINING_SEEDS_V1),
        "training_seed_split": {
            "kind": "FIRST_32_TRAIN_LAST_16_ONE_TIME_TEST",
            "train": list(LEARNED_RESOURCE_FORECAST_TRAIN_SEEDS_V1),
            "test": list(LEARNED_RESOURCE_FORECAST_TEST_SEEDS_V1),
            "all_generator_arms_and_checkpoints_for_one_seed_share_split": True,
        },
        # These top-level names preserve the matched training runtime API.
        "training_tape_prefix": TRAINING_TAPE_PREFIX_V1,
        "evaluation_tape_prefix": MODEL_EVALUATION_TAPE_PREFIX_V1,
        "trajectory_tape_root": TRAJECTORY_TAPE_ROOT_V1,
        "label_tape_root": LABEL_TAPE_ROOT_V1,
        "probe_tape_root": PROBE_TAPE_ROOT_V1,
        "tape_independence_contract": {
            "pairwise_distinct_roots": list(tape_roots),
            "old_u003_u004_u005_v1_v2_evaluation_tapes_reused": False,
        },
        "training": _training_contract_v1(),
        "policy_population_contract": {
            "training_job_count": EXPECTED_TRAINING_JOB_COUNT_V1,
            "model_snapshot_count": EXPECTED_MODEL_SNAPSHOT_COUNT_V1,
            "policy_player_count": EXPECTED_PLAYER_COUNT_V1,
            "checkpoints_are_player_identities_not_independent_training_runs": True,
            (
                "generator_arm_checkpoint_seed_host_model_reward_never_"
                "classifier_inputs"
            ): True,
        },
        "complete_episode_contract": {
            "domain": "EXACT_SYMBOLIC_STANDARD_4_BY_4_2048",
            "ends_on": ["REACH_TILE_2048", "NO_LEGAL_ACTION"],
            "continue_after_2048_score_game": False,
            "all_policy_actions_greedy_legal_and_accepted": True,
            "complete_accepted_action_sequence_retained": True,
            "registered_tape_transition_replay_required": True,
            "cross_device_policy_argmax_reexecution_is_gate": False,
        },
        "self_supervised_trajectory_contract": {
            "eligible_split": "TRAIN_ONLY",
            "train_player_count": 288,
            "episodes_per_player": TRAJECTORY_EPISODES_PER_TRAIN_PLAYER_V1,
            "maximum_windows_per_episode": MAX_WINDOWS_PER_TRAJECTORY_EPISODE_V1,
            "window_selection": {
                "candidate_count": "N=T-8+1",
                "if_N_le_32": "TAKE_ALL_STARTS_0_THROUGH_N_MINUS_1",
                "if_N_gt_32": "START_I=floor(i*(N-1)/31)_FOR_I_0_THROUGH_31",
                "order": "INCREASING_START_INDEX",
            },
            "transitions_per_window": PREFIX_ACTION_COUNT_V1,
            "input_shape": [PREFIX_ACTION_COUNT_V1, GRU_INPUT_WIDTH_V1],
            "input_token": {
                "physical_board_ranks_divided_by_11": 16,
                "action_one_hot": 4,
                "merge_score_coordinate": "log2(merge_score+1)/11",
            },
            "d4_canonicalization_applied": False,
            "future_horizons_accepted_actions": [1, 4, 16],
            "terminal_clamping": True,
            "target_width": FORECAST_TARGET_WIDTH_V1,
            "target_per_horizon": {
                "exact_state_only_resource_coordinates": 16,
                "normalized_cumulative_future_merge_score": (
                    "log2(sum_future_merge_score+1)/11"
                ),
                "terminal_by_horizon_indicator": 1,
            },
            "skill_labels_read": False,
        },
        "skill_label_contract": {
            "episodes_per_player": LABEL_EPISODES_PER_PLAYER_V1,
            "score": "MEAN_TOTAL_MERGE_SCORE",
            "train_quantiles": [
                {"numerator": 1, "denominator": 4},
                {"numerator": 3, "denominator": 4},
            ],
            "quantile_method": "INVERTED_CDF",
            "novice_rule": "SCORE_LE_LOWER_TRAIN_THRESHOLD",
            "expert_rule": "SCORE_GE_UPPER_TRAIN_THRESHOLD",
            "middle_role": "DESCRIPTIVE_ONLY_EXCLUDED_FROM_BINARY_GATE",
            "test_uses_unchanged_train_numeric_thresholds": True,
            "episode_is_measurement_repeat": True,
            "policy_player_is_prediction_unit": True,
            "base_training_seed_is_statistical_cluster": True,
        },
        "probe_contract": {
            "probes_per_player": PROBES_PER_PLAYER_V1,
            "expected_probe_record_count": EXPECTED_PROBE_RECORD_COUNT_V1,
            "accepted_action_count": PREFIX_ACTION_COUNT_V1,
            "available_states": "S0_THROUGH_S8_ONLY",
            "available_actions": "A0_THROUGH_A7_ONLY",
            "available_merge_scores": 8,
            "later_state_outcome_or_other_lane_available": False,
            "episode_ending_before_eight_actions_is_implementation_failure": True,
        },
        "representation_arms": list(PROBE_REPRESENTATION_ARMS_V1),
        "representation_dimensions": dict(PROBE_REPRESENTATION_DIMENSIONS_V1),
        "raw_prefix_contract": {
            "dimension": RAW_PREFIX_DIMENSION_V1,
            "nine_normalized_physical_boards": 144,
            "eight_action_one_hots": 32,
            "eight_normalized_merge_scores": "8_X_log2(merge_score+1)/11",
        },
        "forecast_encoder_contract": {
            "architecture": "ONE_LAYER_GRU_PLUS_LINEAR_FORECAST_HEAD",
            "input_width": GRU_INPUT_WIDTH_V1,
            "hidden_width": GRU_HIDDEN_WIDTH_V1,
            "encoder_parameter_count": 16_704,
            "forecast_target_width": FORECAST_TARGET_WIDTH_V1,
            "encoder_plus_linear_head_parameter_count": 20_214,
            "loss": "MEAN_SQUARED_ERROR_EQUAL_WEIGHT_OVER_ALL_54_TARGETS",
            "initialization_seed": ENCODER_INITIALIZATION_SEED_V1,
            "aligned_and_shuffled_initialization_identical": True,
            "optimizer": "ADAM",
            "learning_rate": {"numerator": 1, "denominator": 1_000},
            "batch_size": FORECAST_BATCH_SIZE_V1,
            "epochs": FORECAST_EPOCHS_V1,
            "early_stopping_or_checkpoint_selection": False,
            "test_players_used": False,
            "forecast_head_discarded_before_labels_opened": True,
            "encoder_frozen_before_labels_opened": True,
            "eligible_epoch": FORECAST_EPOCHS_V1,
            "training_loss_by_epoch_retained_for_diagnosis_only": True,
            "player_shuffled_control": {
                "target_shuffle_seed": TARGET_SHUFFLE_SEED_V1,
                "permute_complete_54_coordinate_rows_within_player": True,
                "player_order": "ASCENDING_PLAYER_ID",
                "within_player_row_order": (
                    "ASCENDING_TAPE_ROOT_EPISODE_INDEX_WINDOW_START"
                ),
                "random_generator": "PYTHON_RANDOM_RANDOM_SHARED_ACROSS_PLAYERS",
                "derangement": (
                    "SATTOLO_I_FROM_N_MINUS_1_DOWN_TO_1_J_RANDRANGE_I"
                ),
                "singleton_rule": "UNCHANGED",
                "preserves_player_target_marginal_and_coordinate_dependence": True,
                "removes_local_future_alignment": True,
            },
        },
        "classifier_contract": {
            "classifier": "L2_LOGISTIC_REGRESSION",
            "one_separate_fit_per_representation": True,
            "standardization": "ELIGIBLE_TRAIN_PROBES_ONLY",
            "constant_coordinates_zero_after_centering": True,
            "intercept_penalized": False,
            "l2_strength": LOGISTIC_L2_STRENGTH_V1,
            "optimizer": "SCIPY_OPTIMIZE_L_BFGS_B_DOUBLE_PRECISION",
            "maximum_iterations": 1_000,
            "ftol": 1e-12,
            "gtol": 1e-8,
            "maximum_line_search_steps": 50,
            "training_class_total_weights": {"NOVICE": "1/2", "EXPERT": "1/2"},
            "every_player_within_class_has_equal_total_weight": True,
            "every_probe_within_player_has_equal_weight": True,
            "predictions_made_once_for_all_eligible_test_probes": True,
        },
        "bootstrap_contract": {
            "kind": "PAIRED_TEST_BASE_SEED_CLUSTER_BOOTSTRAP",
            "cluster_count": 16,
            "replicates": BOOTSTRAP_REPLICATES_V1,
            "random_seed": BOOTSTRAP_RANDOM_SEED_V1,
            "confidence_interval": "PERCENTILE_95_LINEAR_QUANTILE",
            "same_sampled_clusters_for_all_representations": True,
            (
                "undefined_single_class_auroc_replicates_excluded_with_"
                "count_reported"
            ): True,
            "probe_level_is_registered_gate_analysis": True,
            "player_mean_probability_is_descriptive_only": True,
        },
        "prerequisite_contract": {
            "completed_training_jobs": EXPECTED_TRAINING_JOB_COUNT_V1,
            "model_snapshots": EXPECTED_MODEL_SNAPSHOT_COUNT_V1,
            "trajectory_player_artifacts": (
                EXPECTED_TRAJECTORY_PLAYER_ARTIFACT_COUNT_V1
            ),
            "complete_trajectory_episodes": (
                EXPECTED_COMPLETE_TRAJECTORY_EPISODE_COUNT_V1
            ),
            "forecast_encoder_receipts": EXPECTED_FORECAST_ENCODER_RECEIPT_COUNT_V1,
            "frozen_encoder_states": EXPECTED_FROZEN_ENCODER_STATE_COUNT_V1,
            "completed_player_evidence_jobs": EXPECTED_PLAYER_COUNT_V1,
            "failed_player_evidence_jobs": 0,
            "label_aggregates": EXPECTED_PLAYER_COUNT_V1,
            "exact_eight_action_probe_records": EXPECTED_PROBE_RECORD_COUNT_V1,
            "failed_missing_duplicate_or_foreign_identities": 0,
            "minimum_test_expert_players": 16,
            "minimum_test_novice_players": 16,
            "minimum_test_base_seed_clusters_per_class": 8,
        },
        "provisional_design_signal_contract": {
            "aligned_probe_auroc_minimum": {"numerator": 4, "denominator": 5},
            "aligned_probe_auroc_ci95_lower_minimum": {
                "numerator": 3,
                "denominator": 4,
            },
            "aligned_minus_each_control_auroc_ci95_lower_strictly_positive": True,
            "aligned_brier_point_no_greater_than_each_control": True,
            "aligned_minus_each_control_brier_ci95_upper_maximum": {
                "numerator": 1,
                "denominator": 100,
            },
            "all_six_components_must_pass": True,
        },
        "failed_predecessor_boundary": {
            "natural_opening_v1_protocol_id": FAILED_NATURAL_OPENING_PROTOCOL_ID_V1,
            "natural_opening_v1_gate": "FAIL",
            "decision_point_v2_protocol_id": FAILED_DECISION_POINT_PROTOCOL_ID_V1,
            "decision_point_v2_gate": "FAIL",
            (
                "predecessor_policies_labels_states_tapes_features_outcomes_"
                "eligible"
            ): False,
            "u002_is_third_rescue_of_same_hand_designed_representation": False,
        },
        "fresh_successor_boundary": {
            "predecessor_execution_identity": (
                LEARNED_RESOURCE_FORECAST_PREDECESSOR_EXECUTION_IDENTITY_V1
            ),
            "predecessor_ordinal": 1,
            "predecessor_attempt": 1,
            "successor_ordinal": 2,
            "successor_attempt": 1,
            "predecessor_execution_identity_may_be_retried": False,
            "predecessor_seeds_tapes_paths_or_outputs_reused": False,
            "method_and_gate_changed_from_predecessor": False,
        },
        "execution_contract": {
            "global_preflight_runtime_smoke": {
                "required_for_each_worker_and_phase": True,
                "python_implementation": "CPython",
                "device": "cpu",
                "linear_layer_count": 1,
                "module": "torch.nn.Linear",
                "optimizer": "torch.optim.Adam",
                "optimizer_smoke_must_equal_true_before_dispatch_identity": True,
            },
            "policy_training_execution_id_template": (
                "{pilot_execution_identity}:policy-training:{arm}:seed:{seed}"
            ),
            "policy_training_result_basename_template": (
                "{arm_lower}-seed-{seed}.json"
            ),
            "policy_snapshot_basename_template": (
                "{arm_lower}-seed-{seed}-checkpoint-{checkpoint}.pt"
            ),
            "player_evidence_execution_id_template": (
                "{pilot_execution_identity}:player-evidence:{arm}:seed:{seed}:"
                "checkpoint:{checkpoint}"
            ),
            "player_evidence_basename_stem_template": (
                "{arm_lower}-seed-{seed}-checkpoint-{checkpoint}"
            ),
            "train_player_evidence_suffixes": [
                ".trajectory.json",
                ".trajectory.npz",
                ".label.json",
                ".probe.json",
            ],
            "test_player_evidence_suffixes": [".label.json", ".probe.json"],
            "consumed_execution_identity_may_be_retried": False,
            "same_seed_all_arms_and_checkpoints_share_execution_host": True,
            "formal_manifest_must_close_exact_registered_roster": True,
        },
        "claim_boundary": {
            "fresh_exploratory_pilot_only": True,
            "scientific_success": False,
            "scientific_success_claimed": False,
            "positive_result_authorizes_only_fresh_confirmatory_successor": True,
            "negative_result_authorizes_same_representation_rescue": False,
            "human_player_or_visual_ui_transfer_claimed": False,
            "continue_after_2048_game_claimed": False,
            "lmb_transfer_inside_this_gate": False,
            "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
            "SCALAR_CALIBRATION_GATE": "NOT_RUN",
            "BREAK_EVEN_GATE": "NOT_RUN",
            "OFFICIAL_EXECUTION_GATE": "NOT_RUN",
            "official_execution_allowed": False,
        },
        "execution_authorized": False,
        "authorization": "NOT_AUTHORIZED_UNTIL_CLEAN_SOURCE_COMMIT_IS_RATIFIED",
    }


def build_learned_resource_forecast_template_v1() -> dict[str, Any]:
    """Return the complete outcome-free design without execution authority."""

    return _with_identity_v1(_frozen_payload_v1())


def build_ratified_learned_resource_forecast_protocol_v1(
    source_commit: str,
) -> dict[str, Any]:
    """Bind the frozen pilot design to one clean full Git commit."""

    if (
        type(source_commit) is not str
        or re.fullmatch(r"[0-9a-f]{40}", source_commit) is None
    ):
        _fail("ratification source commit must be one lowercase full Git object ID")
    payload = _frozen_payload_v1()
    payload["campaign_kind"] = "LEARNED_RESOURCE_FORECAST_2048_PILOT_U002_RATIFIED"
    payload["source_commit"] = source_commit
    payload["pilot_execution_identity"] = (
        LEARNED_RESOURCE_FORECAST_EXECUTION_IDENTITY_V1
    )
    payload["execution_authorized"] = True
    payload["authorization"] = "RATIFIED_FOR_EXPLORATORY_PILOT_EXECUTION"
    payload["pilot_protocol_ratified"] = True
    return _with_identity_v1(payload)


def validate_learned_resource_forecast_protocol_identity_v1(
    protocol: Mapping[str, Any],
) -> dict[str, Any]:
    """Replay the canonical JSON content identity without granting authority."""

    if type(protocol) is not dict:
        _fail("learned resource-forecast protocol must be a plain object")
    protocol_id = protocol.get("protocol_id")
    if (
        type(protocol_id) is not str
        or re.fullmatch(r"[0-9a-f]{64}", protocol_id) is None
    ):
        _fail("learned resource-forecast protocol identity changed shape")
    payload = dict(protocol)
    del payload["protocol_id"]
    if _with_identity_v1(payload)["protocol_id"] != protocol_id:
        _fail("learned resource-forecast protocol identity is not replayable")
    return dict(protocol)


def validate_ratified_learned_resource_forecast_protocol_v1(
    protocol: Mapping[str, Any],
) -> dict[str, Any]:
    """Accept only the exact frozen design bound to its clean source commit."""

    replayed = validate_learned_resource_forecast_protocol_identity_v1(protocol)
    source_commit = replayed.get("source_commit")
    if type(source_commit) is not str:
        _fail("ratified learned resource-forecast protocol has no source commit")
    expected = build_ratified_learned_resource_forecast_protocol_v1(source_commit)
    if replayed != expected:
        _fail("ratified learned resource-forecast protocol differs from frozen design")
    return replayed


def player_key_v1(base_seed: int, generator_arm: str, checkpoint: int) -> str:
    """Return the public JSON key for one frozen policy-player identity."""

    if (
        type(base_seed) is not int
        or base_seed not in LEARNED_RESOURCE_FORECAST_TRAINING_SEEDS_V1
        or generator_arm not in LEARNED_RESOURCE_FORECAST_ARMS_V1
        or type(checkpoint) is not int
        or checkpoint not in LEARNED_RESOURCE_FORECAST_CHECKPOINTS_V1
    ):
        _fail("policy player identity is outside the frozen U002 roster")
    return f"{base_seed}:{generator_arm}:{checkpoint}"


__all__ = (
    "ALIGNED_FORECAST_ARM_V1",
    "BOOTSTRAP_RANDOM_SEED_V1",
    "BOOTSTRAP_REPLICATES_V1",
    "EXPECTED_MODEL_SNAPSHOT_COUNT_V1",
    "EXPECTED_COMPLETE_TRAJECTORY_EPISODE_COUNT_V1",
    "EXPECTED_FORECAST_ENCODER_RECEIPT_COUNT_V1",
    "EXPECTED_FROZEN_ENCODER_STATE_COUNT_V1",
    "EXPECTED_PLAYER_COUNT_V1",
    "EXPECTED_PROBE_RECORD_COUNT_V1",
    "EXPECTED_TRAJECTORY_PLAYER_ARTIFACT_COUNT_V1",
    "EXPECTED_TRAINING_JOB_COUNT_V1",
    "FORECAST_BATCH_SIZE_V1",
    "FORECAST_EPOCHS_V1",
    "FORECAST_TARGET_WIDTH_V1",
    "GRU_HIDDEN_WIDTH_V1",
    "GRU_INPUT_WIDTH_V1",
    "LABEL_EPISODES_PER_PLAYER_V1",
    "LEARNED_PREFIX_DIMENSION_V1",
    "LEARNED_RESOURCE_FORECAST_ARMS_V1",
    "LEARNED_RESOURCE_FORECAST_CHECKPOINTS_V1",
    "LEARNED_RESOURCE_FORECAST_EXECUTION_IDENTITY_V1",
    "LEARNED_RESOURCE_FORECAST_PROTOCOL_DOMAIN_V1",
    "LEARNED_RESOURCE_FORECAST_PROTOCOL_SCHEMA_V1",
    "LEARNED_RESOURCE_FORECAST_TEST_SEEDS_V1",
    "LEARNED_RESOURCE_FORECAST_TRAINING_SEEDS_V1",
    "LEARNED_RESOURCE_FORECAST_TRAIN_SEEDS_V1",
    "LOGISTIC_L2_STRENGTH_V1",
    "MAX_WINDOWS_PER_TRAJECTORY_EPISODE_V1",
    "PROBES_PER_PLAYER_V1",
    "PROBE_REPRESENTATION_ARMS_V1",
    "PROBE_REPRESENTATION_DIMENSIONS_V1",
    "RAW_PREFIX_ARM_V1",
    "RAW_PREFIX_DIMENSION_V1",
    "SHUFFLED_FORECAST_ARM_V1",
    "TRAJECTORY_EPISODES_PER_TRAIN_PLAYER_V1",
    "LearnedResourceForecastProtocolV1Error",
    "build_learned_resource_forecast_template_v1",
    "build_ratified_learned_resource_forecast_protocol_v1",
    "player_key_v1",
    "validate_learned_resource_forecast_protocol_identity_v1",
    "validate_ratified_learned_resource_forecast_protocol_v1",
)
