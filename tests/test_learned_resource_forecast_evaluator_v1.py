from __future__ import annotations

from copy import deepcopy
import json

import numpy as np
import pytest

from acfqp.science import learned_resource_forecast_evaluator_v1 as evaluator
from acfqp.science import learned_resource_forecast_protocol_v1 as protocol_subject


SOURCE_COMMIT = "8" * 40


@pytest.fixture(scope="module")
def protocol() -> dict:
    return protocol_subject.build_ratified_learned_resource_forecast_protocol_v1(
        SOURCE_COMMIT
    )


def _label_aggregates() -> list[dict]:
    rows = []
    for seed in protocol_subject.LEARNED_RESOURCE_FORECAST_TRAINING_SEEDS_V1:
        for arm_index, arm in enumerate(
            protocol_subject.LEARNED_RESOURCE_FORECAST_ARMS_V1
        ):
            for checkpoint_index, checkpoint in enumerate(
                protocol_subject.LEARNED_RESOURCE_FORECAST_CHECKPOINTS_V1
            ):
                slot = arm_index * 3 + checkpoint_index
                rows.append(
                    {
                        "base_seed": seed,
                        "generator_arm": arm,
                        "checkpoint": checkpoint,
                        "episode_count": 64,
                        "mean_total_merge_score": float(1_000 * slot),
                    }
                )
    return rows


def _probe_matrices() -> dict[str, dict[str, np.ndarray]]:
    matrices = {
        representation: {}
        for representation in protocol_subject.PROBE_REPRESENTATION_ARMS_V1
    }
    for seed in protocol_subject.LEARNED_RESOURCE_FORECAST_TRAINING_SEEDS_V1:
        for arm_index, arm in enumerate(
            protocol_subject.LEARNED_RESOURCE_FORECAST_ARMS_V1
        ):
            for checkpoint_index, checkpoint in enumerate(
                protocol_subject.LEARNED_RESOURCE_FORECAST_CHECKPOINTS_V1
            ):
                slot = arm_index * 3 + checkpoint_index
                key = protocol_subject.player_key_v1(seed, arm, checkpoint)
                raw = np.zeros((16, 184), dtype=np.float64)
                shuffled = np.zeros((16, 248), dtype=np.float64)
                aligned = np.zeros((16, 248), dtype=np.float64)
                if slot <= 2:
                    aligned[:, -1] = -1.0
                elif slot >= 6:
                    aligned[:, -1] = 1.0
                matrices[protocol_subject.RAW_PREFIX_ARM_V1][key] = raw
                matrices[protocol_subject.SHUFFLED_FORECAST_ARM_V1][key] = shuffled
                matrices[protocol_subject.ALIGNED_FORECAST_ARM_V1][key] = aligned
    return matrices


def _complete_counts() -> dict[str, int]:
    return {
        "completed_training_jobs": 144,
        "failed_training_jobs": 0,
        "model_snapshots": 432,
        "trajectory_player_artifacts": 288,
        "complete_trajectory_episodes": 4_608,
        "forecast_encoder_receipts": 2,
        "frozen_encoder_states": 2,
        "completed_player_evidence_jobs": 432,
        "failed_player_evidence_jobs": 0,
        "label_aggregates": 432,
        "exact_eight_action_probe_records": 6_912,
        "missing_identities": 0,
        "duplicate_identities": 0,
        "foreign_identities": 0,
    }


@pytest.fixture(scope="module")
def passing_result(protocol: dict) -> dict:
    return evaluator.evaluate_learned_resource_forecast_pilot_v1(
        protocol,
        _label_aggregates(),
        _probe_matrices(),
        _complete_counts(),
    )


def test_metrics_and_fixed_logistic_class_player_weighting() -> None:
    assert evaluator.tie_safe_auroc_v1([0, 0, 1, 1], [0.5] * 4) == 0.5
    assert evaluator.tie_safe_auroc_v1([0, 0, 1, 1], [0.1, 0.2, 0.8, 0.9]) == 1.0
    assert evaluator.brier_score_v1([0, 1], [0.0, 1.0]) == 0.0

    features = np.zeros((4 * 16, 1), dtype=np.float64)
    labels = np.concatenate(
        (np.zeros(2 * 16, dtype=np.int64), np.ones(2 * 16, dtype=np.int64))
    )
    players = np.repeat(np.arange(4, dtype=np.int64), 16)
    probabilities = evaluator._fit_classifier_probabilities_v1(  # noqa: SLF001
        features,
        labels,
        players,
        np.zeros((16, 1), dtype=np.float64),
    )
    assert np.all(probabilities == 0.5)


def test_full_heldout_gate_uses_inverted_cdf_and_paired_seed_bootstrap(
    passing_result: dict,
) -> None:
    json.dumps(passing_result, allow_nan=False, sort_keys=True)
    assert passing_result["PROVISIONAL_DESIGN_SIGNAL_GATE"] == "PASS"
    assert passing_result["scientific_success"] is False
    assert passing_result["scientific_success_claimed"] is False
    assert passing_result["skill_thresholds"] == {
        "method": "INVERTED_CDF_ON_288_TRAIN_PLAYERS",
        "lower_25_percent": 2000.0,
        "upper_75_percent": 6000.0,
        "applied_unchanged_to_test": True,
    }
    assert passing_result["prerequisite_counts"]["test_expert_players"] == 48
    assert passing_result["prerequisite_counts"]["test_novice_players"] == 48
    assert passing_result["prerequisite_counts"][
        "test_expert_base_seed_clusters"
    ] == 16
    assert passing_result["prerequisite_counts"][
        "test_novice_base_seed_clusters"
    ] == 16
    assert all(passing_result["prerequisite_components"].values())
    assert len(passing_result["provisional_design_signal_components"]) == 6
    assert all(passing_result["provisional_design_signal_components"].values())
    candidate = passing_result["metrics"][
        protocol_subject.ALIGNED_FORECAST_ARM_V1
    ]["probe_level"]
    assert candidate["auroc"] == 1.0
    assert candidate["auroc_ci95"]["lower"] == 1.0
    assert candidate["auroc_defined_bootstrap_replicates"] == 20_000
    assert passing_result["metrics"][protocol_subject.RAW_PREFIX_ARM_V1][
        "probe_level"
    ]["auroc"] == 0.5
    assert passing_result["bootstrap"] == {
        "kind": "PAIRED_TEST_BASE_SEED_CLUSTER_BOOTSTRAP",
        "cluster_count": 16,
        "replicates": 20_000,
        "random_seed": 881_003,
        "confidence_interval": "PERCENTILE_95_LINEAR_QUANTILE",
    }


def test_prerequisite_failure_does_not_run_or_reinterpret_the_gate(
    protocol: dict,
) -> None:
    counts = _complete_counts()
    counts["model_snapshots"] = 431
    result = evaluator.evaluate_learned_resource_forecast_pilot_v1(
        protocol,
        _label_aggregates(),
        _probe_matrices(),
        counts,
    )

    assert result["PROVISIONAL_DESIGN_SIGNAL_GATE"] == "FAIL_PREREQUISITE_GATES"
    assert result["metrics"] is None
    assert result["test_probe_predictions"] == []
    assert not result["prerequisite_components"][
        "exact_432_model_snapshots_present"
    ]
    assert not any(result["provisional_design_signal_components"].values())


def test_evaluator_rejects_foreign_player_or_feature_shape(protocol: dict) -> None:
    labels = _label_aggregates()
    labels[0]["base_seed"] = 1
    with pytest.raises(
        evaluator.LearnedResourceForecastEvaluatorV1Error,
        match="registered 64-episode",
    ):
        evaluator.evaluate_learned_resource_forecast_pilot_v1(
            protocol, labels, _probe_matrices(), _complete_counts()
        )

    matrices = _probe_matrices()
    representation = protocol_subject.ALIGNED_FORECAST_ARM_V1
    key = next(iter(matrices[representation]))
    matrices[representation][key] = np.zeros((16, 247), dtype=np.float64)
    with pytest.raises(
        evaluator.LearnedResourceForecastEvaluatorV1Error,
        match="feature shape",
    ):
        evaluator.evaluate_learned_resource_forecast_pilot_v1(
            protocol, _label_aggregates(), matrices, _complete_counts()
        )

    matrices = _probe_matrices()
    representation = protocol_subject.SHUFFLED_FORECAST_ARM_V1
    key = next(iter(matrices[representation]))
    matrices[representation][key][0, 0] = 1.0
    with pytest.raises(
        evaluator.LearnedResourceForecastEvaluatorV1Error,
        match="raw prefix block",
    ):
        evaluator.evaluate_learned_resource_forecast_pilot_v1(
            protocol, _label_aggregates(), matrices, _complete_counts()
        )
