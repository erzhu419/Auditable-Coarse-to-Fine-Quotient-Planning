from __future__ import annotations

from copy import deepcopy

import pytest

from acfqp.science import learned_resource_forecast_2048_v1 as core
from acfqp.science import learned_resource_forecast_protocol_v1 as subject


SOURCE_COMMIT = "7" * 40


def test_ratified_protocol_freezes_population_lanes_and_runtime_api() -> None:
    protocol = subject.build_ratified_learned_resource_forecast_protocol_v1(
        SOURCE_COMMIT
    )

    assert protocol["source_commit"] == SOURCE_COMMIT
    assert protocol["pilot_execution_identity"] == (
        "acfqp-learned-resource-forecast-2048-pilot-u002-ordinal2-attempt1"
    )
    assert protocol["arms"] == [
        "RAW_BOARD_STANDARD",
        "RAW_PLUS_ROTATED_RAW_CONTROL",
        "RAW_PLUS_RESOURCE_STATE_ONLY",
    ]
    assert protocol["training_seeds"] == list(range(782_101, 782_149))
    assert protocol["training_seed_split"]["train"] == list(
        range(782_101, 782_133)
    )
    assert protocol["training_seed_split"]["test"] == list(
        range(782_133, 782_149)
    )
    assert protocol["training"]["evaluation_checkpoints"] == [
        25_000,
        50_000,
        100_000,
    ]
    assert protocol["training"]["environment_steps_per_seed_arm"] == 100_000
    assert protocol["training_tape_prefix"]
    assert protocol["evaluation_tape_prefix"]
    roots = protocol["tape_independence_contract"]["pairwise_distinct_roots"]
    assert roots == [
        "acfqp-learned-resource-forecast-u002-policy-training-v1",
        "acfqp-learned-resource-forecast-u002-model-evaluation-v1",
        "acfqp-learned-resource-forecast-u002-self-supervised-trajectory-v1",
        "acfqp-learned-resource-forecast-u002-skill-label-v1",
        "acfqp-learned-resource-forecast-u002-eight-action-probe-v1",
    ]
    assert len(roots) == len(set(roots)) == 5
    assert protocol["policy_population_contract"] == {
        "training_job_count": 144,
        "model_snapshot_count": 432,
        "policy_player_count": 432,
        "checkpoints_are_player_identities_not_independent_training_runs": True,
        "generator_arm_checkpoint_seed_host_model_reward_never_classifier_inputs": True,
    }
    assert protocol["execution_contract"]["global_preflight_runtime_smoke"] == {
        "required_for_each_worker_and_phase": True,
        "python_implementation": "CPython",
        "device": "cpu",
        "linear_layer_count": 1,
        "module": "torch.nn.Linear",
        "optimizer": "torch.optim.Adam",
        "optimizer_smoke_must_equal_true_before_dispatch_identity": True,
    }
    assert protocol["fresh_successor_boundary"] == {
        "predecessor_execution_identity": (
            "acfqp-learned-resource-forecast-2048-pilot-u001-ordinal1-attempt1"
        ),
        "predecessor_ordinal": 1,
        "predecessor_attempt": 1,
        "successor_ordinal": 2,
        "successor_attempt": 1,
        "predecessor_execution_identity_may_be_retried": False,
        "predecessor_seeds_tapes_paths_or_outputs_reused": False,
        "method_and_gate_changed_from_predecessor": False,
    }
    assert subject.validate_ratified_learned_resource_forecast_protocol_v1(
        protocol
    ) == protocol


def test_protocol_freezes_exact_encoder_classifier_bootstrap_and_gate() -> None:
    protocol = subject.build_ratified_learned_resource_forecast_protocol_v1(
        SOURCE_COMMIT
    )
    trajectory = protocol["self_supervised_trajectory_contract"]
    encoder = protocol["forecast_encoder_contract"]

    assert trajectory["episodes_per_player"] == 16
    assert trajectory["maximum_windows_per_episode"] == 32
    assert trajectory["window_selection"] == {
        "candidate_count": "N=T-8+1",
        "if_N_le_32": "TAKE_ALL_STARTS_0_THROUGH_N_MINUS_1",
        "if_N_gt_32": "START_I=floor(i*(N-1)/31)_FOR_I_0_THROUGH_31",
        "order": "INCREASING_START_INDEX",
    }
    assert trajectory["input_shape"] == [8, 21]
    assert trajectory["input_token"]["merge_score_coordinate"] == (
        "log2(merge_score+1)/11"
    )
    assert trajectory["target_width"] == 54
    assert trajectory["target_per_horizon"][
        "normalized_cumulative_future_merge_score"
    ] == "log2(sum_future_merge_score+1)/11"
    assert encoder["architecture"] == "ONE_LAYER_GRU_PLUS_LINEAR_FORECAST_HEAD"
    assert encoder["hidden_width"] == 64
    assert encoder["encoder_parameter_count"] == 16_704
    assert encoder["encoder_plus_linear_head_parameter_count"] == 20_214
    assert encoder["epochs"] == 50
    assert encoder["loss"] == "MEAN_SQUARED_ERROR_EQUAL_WEIGHT_OVER_ALL_54_TARGETS"
    assert encoder["player_shuffled_control"]["target_shuffle_seed"] == 881_002
    assert encoder["player_shuffled_control"]["derangement"] == (
        "SATTOLO_I_FROM_N_MINUS_1_DOWN_TO_1_J_RANDRANGE_I"
    )
    assert protocol["classifier_contract"]["l2_strength"] == 1.0
    assert protocol["bootstrap_contract"]["replicates"] == 20_000
    assert protocol["provisional_design_signal_contract"][
        "all_six_components_must_pass"
    ]
    assert not protocol["claim_boundary"]["scientific_success_claimed"]
    assert not protocol["claim_boundary"]["official_execution_allowed"]

    assert core.PREFIX_TOKEN_WIDTH_V1 == 21
    assert core.FORECAST_HIDDEN_WIDTH_V1 == 64
    assert core.FORECAST_TARGET_DIMENSION_V1 == 54
    assert core.MAX_WINDOWS_PER_COMPLETE_TRAJECTORY_V1 == 32
    assert core.FORECAST_TRAINING_EPOCHS_V1 == 50
    assert core.FORECAST_BATCH_SIZE_V1 == 256
    assert core.TARGET_SHUFFLE_SEED_V1 == 881_002


def test_template_is_unauthorized_and_identity_or_template_drift_is_rejected() -> None:
    template = subject.build_learned_resource_forecast_template_v1()
    assert template["source_commit"] is None
    assert not template["execution_authorized"]
    with pytest.raises(
        subject.LearnedResourceForecastProtocolV1Error,
        match="no source commit",
    ):
        subject.validate_ratified_learned_resource_forecast_protocol_v1(template)

    with pytest.raises(
        subject.LearnedResourceForecastProtocolV1Error,
        match="full Git object ID",
    ):
        subject.build_ratified_learned_resource_forecast_protocol_v1("short")

    protocol = subject.build_ratified_learned_resource_forecast_protocol_v1(
        SOURCE_COMMIT
    )
    tampered = deepcopy(protocol)
    tampered["training_seeds"][0] += 1
    with pytest.raises(
        subject.LearnedResourceForecastProtocolV1Error,
        match="not replayable",
    ):
        subject.validate_ratified_learned_resource_forecast_protocol_v1(tampered)

    resigned = deepcopy(protocol)
    resigned["training_seeds"][0] += 1
    payload = dict(resigned)
    del payload["protocol_id"]
    resigned = subject._with_identity_v1(payload)  # noqa: SLF001
    with pytest.raises(
        subject.LearnedResourceForecastProtocolV1Error,
        match="differs from frozen design",
    ):
        subject.validate_ratified_learned_resource_forecast_protocol_v1(resigned)
