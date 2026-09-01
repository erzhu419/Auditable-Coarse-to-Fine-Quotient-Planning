"""Frozen held-out evaluator for the learned resource-forecast 2048 pilot.

The evaluator consumes abstract label aggregates and probe matrices.  It has
no model-path, host, reward, generator-arm metadata, or trajectory-loader
feature path: generator identity is used only to close the registered player
roster and never becomes a classifier coordinate.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import math
from typing import Any, NoReturn

import numpy as np
from scipy.optimize import minimize
from scipy.special import expit

from acfqp.science.learned_resource_forecast_protocol_v1 import (
    ALIGNED_FORECAST_ARM_V1,
    BOOTSTRAP_RANDOM_SEED_V1,
    BOOTSTRAP_REPLICATES_V1,
    EXPECTED_COMPLETE_TRAJECTORY_EPISODE_COUNT_V1,
    EXPECTED_FORECAST_ENCODER_RECEIPT_COUNT_V1,
    EXPECTED_FROZEN_ENCODER_STATE_COUNT_V1,
    EXPECTED_MODEL_SNAPSHOT_COUNT_V1,
    EXPECTED_PLAYER_COUNT_V1,
    EXPECTED_PROBE_RECORD_COUNT_V1,
    EXPECTED_TRAINING_JOB_COUNT_V1,
    EXPECTED_TRAJECTORY_PLAYER_ARTIFACT_COUNT_V1,
    LABEL_EPISODES_PER_PLAYER_V1,
    LEARNED_RESOURCE_FORECAST_ARMS_V1,
    LEARNED_RESOURCE_FORECAST_CHECKPOINTS_V1,
    LEARNED_RESOURCE_FORECAST_TEST_SEEDS_V1,
    LEARNED_RESOURCE_FORECAST_TRAINING_SEEDS_V1,
    LEARNED_RESOURCE_FORECAST_TRAIN_SEEDS_V1,
    LOGISTIC_L2_STRENGTH_V1,
    PROBES_PER_PLAYER_V1,
    PROBE_REPRESENTATION_ARMS_V1,
    PROBE_REPRESENTATION_DIMENSIONS_V1,
    RAW_PREFIX_ARM_V1,
    SHUFFLED_FORECAST_ARM_V1,
    player_key_v1,
    validate_ratified_learned_resource_forecast_protocol_v1,
)


LEARNED_RESOURCE_FORECAST_EVALUATION_SCHEMA_V1 = (
    "acfqp.science.learned_resource_forecast_2048_pilot_evaluation.v1"
)

_LABEL_AGGREGATE_FIELDS = frozenset(
    {
        "base_seed",
        "generator_arm",
        "checkpoint",
        "episode_count",
        "mean_total_merge_score",
    }
)
_PREREQUISITE_COUNT_FIELDS = frozenset(
    {
        "completed_training_jobs",
        "failed_training_jobs",
        "model_snapshots",
        "trajectory_player_artifacts",
        "complete_trajectory_episodes",
        "forecast_encoder_receipts",
        "frozen_encoder_states",
        "completed_player_evidence_jobs",
        "failed_player_evidence_jobs",
        "label_aggregates",
        "exact_eight_action_probe_records",
        "missing_identities",
        "duplicate_identities",
        "foreign_identities",
    }
)


class LearnedResourceForecastEvaluatorV1Error(ValueError):
    """The abstract evidence or frozen statistical analysis is invalid."""


def _fail(message: str) -> NoReturn:
    raise LearnedResourceForecastEvaluatorV1Error(message)


def _validate_supported_measurement_protocol_v1(
    protocol: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate U002 or the exact fixed-policy U003 evidence successor."""

    campaign_kind = protocol.get("campaign_kind") if type(protocol) is dict else None
    if campaign_kind == (
        "LEARNED_RESOURCE_FORECAST_2048_FIXED_POLICY_"
        "EVIDENCE_SUCCESSOR_U003_RATIFIED"
    ):
        from acfqp.science.learned_resource_forecast_evidence_successor_protocol_v1 import (
            validate_ratified_learned_resource_forecast_evidence_successor_protocol_v1,
        )

        return validate_ratified_learned_resource_forecast_evidence_successor_protocol_v1(
            protocol
        )
    return validate_ratified_learned_resource_forecast_protocol_v1(protocol)


def _finite_number(value: Any) -> bool:
    return type(value) in (int, float) and math.isfinite(float(value))


def tie_safe_auroc_v1(labels: Sequence[int], scores: Sequence[float]) -> float:
    """Return rank AUROC with average credit for score ties."""

    y = np.asarray(labels)
    values = np.asarray(scores, dtype=np.float64)
    if (
        y.ndim != 1
        or values.ndim != 1
        or len(y) != len(values)
        or len(y) == 0
        or not np.all(np.isfinite(values))
        or not np.all((y == 0) | (y == 1))
    ):
        _fail("AUROC inputs must be paired finite binary rows")
    positive = values[y == 1]
    negative = values[y == 0]
    if len(positive) == 0 or len(negative) == 0:
        _fail("AUROC requires both policy labels")
    concordance = np.sum(positive[:, None] > negative[None, :])
    ties = np.sum(positive[:, None] == negative[None, :])
    return float((concordance + 0.5 * ties) / (len(positive) * len(negative)))


def brier_score_v1(labels: Sequence[int], probabilities: Sequence[float]) -> float:
    """Return the ordinary probe- or player-level binary Brier score."""

    y = np.asarray(labels, dtype=np.float64)
    values = np.asarray(probabilities, dtype=np.float64)
    if (
        y.ndim != 1
        or values.ndim != 1
        or len(y) != len(values)
        or len(y) == 0
        or not np.all((y == 0) | (y == 1))
        or not np.all(np.isfinite(values))
        or not np.all((0 <= values) & (values <= 1))
    ):
        _fail("Brier inputs must be paired binary labels and probabilities")
    return float(np.mean((values - y) ** 2))


def _registered_player_keys() -> tuple[str, ...]:
    return tuple(
        player_key_v1(seed, arm, checkpoint)
        for seed in LEARNED_RESOURCE_FORECAST_TRAINING_SEEDS_V1
        for arm in LEARNED_RESOURCE_FORECAST_ARMS_V1
        for checkpoint in LEARNED_RESOURCE_FORECAST_CHECKPOINTS_V1
    )


def _validate_label_aggregates(
    value: Sequence[Mapping[str, Any]],
) -> tuple[dict[str, float], dict[str, tuple[int, str, int]]]:
    if (
        not isinstance(value, Sequence)
        or isinstance(value, (str, bytes))
        or len(value) != EXPECTED_PLAYER_COUNT_V1
        or any(
            type(row) is not dict or set(row) != _LABEL_AGGREGATE_FIELDS
            for row in value
        )
    ):
        _fail("label aggregates must contain the exact 432-player field roster")
    scores: dict[str, float] = {}
    identities: dict[str, tuple[int, str, int]] = {}
    for row in value:
        seed = row["base_seed"]
        arm = row["generator_arm"]
        checkpoint = row["checkpoint"]
        if (
            type(seed) is not int
            or seed not in LEARNED_RESOURCE_FORECAST_TRAINING_SEEDS_V1
            or arm not in LEARNED_RESOURCE_FORECAST_ARMS_V1
            or type(checkpoint) is not int
            or checkpoint not in LEARNED_RESOURCE_FORECAST_CHECKPOINTS_V1
            or row["episode_count"] != LABEL_EPISODES_PER_PLAYER_V1
            or not _finite_number(row["mean_total_merge_score"])
            or float(row["mean_total_merge_score"]) < 0.0
        ):
            _fail("label aggregate is not one registered 64-episode finite mean")
        key = player_key_v1(seed, arm, checkpoint)
        if key in scores:
            _fail("label aggregates repeat a policy-player identity")
        scores[key] = float(row["mean_total_merge_score"])
        identities[key] = (seed, arm, checkpoint)
    if set(scores) != set(_registered_player_keys()):
        _fail("label aggregates do not close the exact frozen player roster")
    return scores, identities


def assign_skill_labels_v1(
    scores: Mapping[str, float],
    identities: Mapping[str, tuple[int, str, int]],
) -> tuple[dict[str, str], float, float]:
    """Apply train-only inverted-CDF thresholds unchanged to all players."""

    train_scores = np.asarray(
        [
            scores[key]
            for key in _registered_player_keys()
            if identities[key][0] in LEARNED_RESOURCE_FORECAST_TRAIN_SEEDS_V1
        ],
        dtype=np.float64,
    )
    if train_scores.shape != (288,) or not np.all(np.isfinite(train_scores)):
        _fail("train label score roster changed")
    lower, upper = np.quantile(
        train_scores, (0.25, 0.75), method="inverted_cdf"
    )
    labels: dict[str, str] = {}
    for key in _registered_player_keys():
        score = scores[key]
        if score <= lower:
            labels[key] = "NOVICE"
        elif score >= upper:
            labels[key] = "EXPERT"
        else:
            labels[key] = "EXCLUDED_MIDDLE"
    return labels, float(lower), float(upper)


def _validate_probe_matrices(
    value: Mapping[str, Mapping[str, Any]],
) -> dict[str, dict[str, np.ndarray]]:
    if not isinstance(value, Mapping) or set(value) != set(
        PROBE_REPRESENTATION_ARMS_V1
    ):
        _fail("probe matrices must contain the exact three representation arms")
    expected_keys = set(_registered_player_keys())
    result: dict[str, dict[str, np.ndarray]] = {}
    for representation in PROBE_REPRESENTATION_ARMS_V1:
        raw_arm = value[representation]
        if not isinstance(raw_arm, Mapping) or set(raw_arm) != expected_keys:
            _fail("probe matrix arm does not close the exact 432-player roster")
        dimension = PROBE_REPRESENTATION_DIMENSIONS_V1[representation]
        arm_matrices: dict[str, np.ndarray] = {}
        for key in _registered_player_keys():
            try:
                matrix = np.asarray(raw_arm[key], dtype=np.float64)
            except (TypeError, ValueError) as error:
                raise LearnedResourceForecastEvaluatorV1Error(
                    "probe matrix is not numeric"
                ) from error
            if (
                matrix.shape != (PROBES_PER_PLAYER_V1, dimension)
                or not np.all(np.isfinite(matrix))
            ):
                _fail("probe matrix changed its frozen 16-row feature shape")
            arm_matrices[key] = matrix
        result[representation] = arm_matrices
    for key in _registered_player_keys():
        raw = result[RAW_PREFIX_ARM_V1][key]
        for representation in (
            SHUFFLED_FORECAST_ARM_V1,
            ALIGNED_FORECAST_ARM_V1,
        ):
            if not np.array_equal(
                result[representation][key][:, : raw.shape[1]], raw
            ):
                _fail("learned representation raw prefix block differs from raw arm")
    return result


def _validate_prerequisite_counts(value: Mapping[str, Any]) -> dict[str, int]:
    if type(value) is not dict or set(value) != _PREREQUISITE_COUNT_FIELDS:
        _fail("prerequisite count field set changed")
    if any(type(item) is not int or item < 0 for item in value.values()):
        _fail("prerequisite counts must be nonnegative exact integers")
    return dict(value)


def _fit_classifier_probabilities_v1(
    training_features: np.ndarray,
    training_labels: np.ndarray,
    training_player_indices: np.ndarray,
    heldout_features: np.ndarray,
) -> np.ndarray:
    """Fit the fixed player- and class-equal L2 logistic classifier."""

    x_raw = np.asarray(training_features, dtype=np.float64)
    y = np.asarray(training_labels)
    player_indices = np.asarray(training_player_indices)
    x_test_raw = np.asarray(heldout_features, dtype=np.float64)
    if (
        x_raw.ndim != 2
        or x_test_raw.ndim != 2
        or x_raw.shape[1] != x_test_raw.shape[1]
        or y.shape != (x_raw.shape[0],)
        or player_indices.shape != (x_raw.shape[0],)
        or not np.all(np.isfinite(x_raw))
        or not np.all(np.isfinite(x_test_raw))
        or not np.all((y == 0) | (y == 1))
        or not np.issubdtype(player_indices.dtype, np.integer)
    ):
        _fail("fixed logistic arrays have incompatible shapes or values")
    means = np.mean(x_raw, axis=0)
    scales = np.std(x_raw, axis=0, ddof=0)
    scales = np.where(scales == 0.0, 1.0, scales)
    x_train = (x_raw - means) / scales
    x_test = (x_test_raw - means) / scales
    labels = y.astype(np.float64)

    unique_players = np.unique(player_indices)
    player_label: dict[int, int] = {}
    for player in unique_players:
        rows = labels[player_indices == player]
        if len(rows) != PROBES_PER_PLAYER_V1 or not np.all(rows == rows[0]):
            _fail("each training player must contribute 16 probes with one label")
        player_label[int(player)] = int(rows[0])
    class_players = {
        label: [player for player, value in player_label.items() if value == label]
        for label in (0, 1)
    }
    if any(not players for players in class_players.values()):
        _fail("fixed logistic training requires both skill classes")
    sample_weights = np.empty(len(labels), dtype=np.float64)
    for row_index, (label, player) in enumerate(zip(y, player_indices, strict=True)):
        sample_weights[row_index] = 0.5 / (
            len(class_players[int(label)]) * PROBES_PER_PLAYER_V1
        )
        if int(player) not in class_players[int(label)]:
            _fail("training player index is inconsistent with its class")

    def objective(parameters: np.ndarray) -> tuple[float, np.ndarray]:
        weights = parameters[:-1]
        intercept = parameters[-1]
        logits = x_train @ weights + intercept
        loss = float(
            np.sum(
                sample_weights
                * (np.logaddexp(0.0, logits) - labels * logits)
            )
            + 0.5 * LOGISTIC_L2_STRENGTH_V1 * np.dot(weights, weights)
        )
        residual = sample_weights * (expit(logits) - labels)
        gradient = np.concatenate(
            (
                x_train.T @ residual + LOGISTIC_L2_STRENGTH_V1 * weights,
                np.asarray([np.sum(residual)]),
            )
        )
        return loss, gradient

    fit = minimize(
        objective,
        np.zeros(x_train.shape[1] + 1, dtype=np.float64),
        method="L-BFGS-B",
        jac=True,
        options={"maxiter": 1_000, "ftol": 1e-12, "gtol": 1e-8, "maxls": 50},
    )
    if not fit.success or not np.all(np.isfinite(fit.x)):
        _fail(f"fixed L-BFGS fit failed: {fit.message}")
    probabilities = expit(x_test @ fit.x[:-1] + fit.x[-1])
    if (
        probabilities.shape != (x_test.shape[0],)
        or not np.all(np.isfinite(probabilities))
    ):
        _fail("held-out probability shape changed")
    return probabilities


def _fit_three_classifiers(
    labels: Mapping[str, str],
    identities: Mapping[str, tuple[int, str, int]],
    matrices: Mapping[str, Mapping[str, np.ndarray]],
) -> dict[str, dict[str, np.ndarray]]:
    train_keys = [
        key
        for key in _registered_player_keys()
        if identities[key][0] in LEARNED_RESOURCE_FORECAST_TRAIN_SEEDS_V1
        and labels[key] != "EXCLUDED_MIDDLE"
    ]
    test_keys = [
        key
        for key in _registered_player_keys()
        if identities[key][0] in LEARNED_RESOURCE_FORECAST_TEST_SEEDS_V1
        and labels[key] != "EXCLUDED_MIDDLE"
    ]
    numeric = {key: int(labels[key] == "EXPERT") for key in train_keys + test_keys}
    training_labels = np.concatenate(
        [
            np.full(PROBES_PER_PLAYER_V1, numeric[key], dtype=np.int64)
            for key in train_keys
        ]
    )
    training_player_indices = np.concatenate(
        [
            np.full(PROBES_PER_PLAYER_V1, index, dtype=np.int64)
            for index, _key in enumerate(train_keys)
        ]
    )
    predictions: dict[str, dict[str, np.ndarray]] = {}
    for representation in PROBE_REPRESENTATION_ARMS_V1:
        training_features = np.concatenate(
            [matrices[representation][key] for key in train_keys], axis=0
        )
        heldout_features = np.concatenate(
            [matrices[representation][key] for key in test_keys], axis=0
        )
        flat = _fit_classifier_probabilities_v1(
            training_features,
            training_labels,
            training_player_indices,
            heldout_features,
        )
        predictions[representation] = {
            key: flat[
                index * PROBES_PER_PLAYER_V1 : (index + 1) * PROBES_PER_PLAYER_V1
            ]
            for index, key in enumerate(test_keys)
        }
    return predictions


def _level_rows(
    labels: Mapping[str, str],
    identities: Mapping[str, tuple[int, str, int]],
    probabilities: Mapping[str, np.ndarray],
    *,
    player_level: bool,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    row_labels: list[int] = []
    row_scores: list[float] = []
    row_seed_indices: list[int] = []
    seed_to_index = {
        seed: index
        for index, seed in enumerate(LEARNED_RESOURCE_FORECAST_TEST_SEEDS_V1)
    }
    for key in _registered_player_keys():
        seed = identities[key][0]
        if seed not in seed_to_index or labels[key] == "EXCLUDED_MIDDLE":
            continue
        values = probabilities[key]
        if player_level:
            values = np.asarray([np.mean(values)], dtype=np.float64)
        row_labels.extend([int(labels[key] == "EXPERT")] * len(values))
        row_scores.extend(float(value) for value in values)
        row_seed_indices.extend([seed_to_index[seed]] * len(values))
    return (
        np.asarray(row_labels, dtype=np.int64),
        np.asarray(row_scores, dtype=np.float64),
        np.asarray(row_seed_indices, dtype=np.int64),
    )


def _cluster_metric_arrays(
    labels: np.ndarray,
    scores: np.ndarray,
    seed_indices: np.ndarray,
    cluster_counts: np.ndarray,
) -> tuple[float, float, np.ndarray, np.ndarray]:
    point_auroc = tie_safe_auroc_v1(labels, scores)
    point_brier = brier_score_v1(labels, scores)
    cluster_count = len(LEARNED_RESOURCE_FORECAST_TEST_SEEDS_V1)
    positive_count = np.zeros(cluster_count, dtype=np.float64)
    negative_count = np.zeros(cluster_count, dtype=np.float64)
    squared_error_sum = np.zeros(cluster_count, dtype=np.float64)
    row_count = np.zeros(cluster_count, dtype=np.float64)
    concordance = np.zeros((cluster_count, cluster_count), dtype=np.float64)
    for seed in range(cluster_count):
        in_seed = seed_indices == seed
        positive_count[seed] = np.sum(in_seed & (labels == 1))
        negative_count[seed] = np.sum(in_seed & (labels == 0))
        squared_error_sum[seed] = np.sum((scores[in_seed] - labels[in_seed]) ** 2)
        row_count[seed] = np.sum(in_seed)
    for positive_seed in range(cluster_count):
        positive = scores[(seed_indices == positive_seed) & (labels == 1)]
        for negative_seed in range(cluster_count):
            negative = scores[(seed_indices == negative_seed) & (labels == 0)]
            if len(positive) and len(negative):
                concordance[positive_seed, negative_seed] = float(
                    np.sum(positive[:, None] > negative[None, :])
                    + 0.5 * np.sum(positive[:, None] == negative[None, :])
                )
    positive_total = cluster_counts @ positive_count
    negative_total = cluster_counts @ negative_count
    numerator = np.einsum(
        "bi,ij,bj->b", cluster_counts, concordance, cluster_counts, optimize=True
    )
    denominator = positive_total * negative_total
    bootstrap_auroc = np.full(len(cluster_counts), np.nan, dtype=np.float64)
    valid = denominator > 0
    bootstrap_auroc[valid] = numerator[valid] / denominator[valid]
    bootstrap_brier = (cluster_counts @ squared_error_sum) / (
        cluster_counts @ row_count
    )
    return point_auroc, point_brier, bootstrap_auroc, bootstrap_brier


def _interval(values: np.ndarray) -> dict[str, float]:
    finite = values[np.isfinite(values)]
    if len(finite) == 0:
        _fail("bootstrap produced no defined metric replicates")
    lower, upper = np.quantile(finite, (0.025, 0.975), method="linear")
    return {"lower": float(lower), "upper": float(upper)}


def _metric_document(
    point_auroc: float,
    point_brier: float,
    bootstrap_auroc: np.ndarray,
    bootstrap_brier: np.ndarray,
) -> dict[str, Any]:
    return {
        "auroc": float(point_auroc),
        "auroc_ci95": _interval(bootstrap_auroc),
        "auroc_defined_bootstrap_replicates": int(np.sum(np.isfinite(bootstrap_auroc))),
        "brier": float(point_brier),
        "brier_ci95": _interval(bootstrap_brier),
    }


def _metrics_and_comparisons(
    labels: Mapping[str, str],
    identities: Mapping[str, tuple[int, str, int]],
    predictions: Mapping[str, Mapping[str, np.ndarray]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    generator = np.random.default_rng(BOOTSTRAP_RANDOM_SEED_V1)
    draws = generator.integers(
        0,
        len(LEARNED_RESOURCE_FORECAST_TEST_SEEDS_V1),
        size=(BOOTSTRAP_REPLICATES_V1, len(LEARNED_RESOURCE_FORECAST_TEST_SEEDS_V1)),
    )
    cluster_counts = np.zeros(
        (BOOTSTRAP_REPLICATES_V1, len(LEARNED_RESOURCE_FORECAST_TEST_SEEDS_V1)),
        dtype=np.float64,
    )
    rows = np.arange(BOOTSTRAP_REPLICATES_V1)[:, None]
    np.add.at(cluster_counts, (rows, draws), 1.0)

    arrays: dict[str, dict[str, tuple[float, float, np.ndarray, np.ndarray]]] = {
        "probe_level": {},
        "player_mean_probability": {},
    }
    for level, player_level in (
        ("probe_level", False),
        ("player_mean_probability", True),
    ):
        for representation in PROBE_REPRESENTATION_ARMS_V1:
            y, score, seed_index = _level_rows(
                labels,
                identities,
                predictions[representation],
                player_level=player_level,
            )
            arrays[level][representation] = _cluster_metric_arrays(
                y, score, seed_index, cluster_counts
            )

    metrics = {
        representation: {
            level: _metric_document(*arrays[level][representation])
            for level in arrays
        }
        for representation in PROBE_REPRESENTATION_ARMS_V1
    }
    comparisons: dict[str, Any] = {}
    for control in (RAW_PREFIX_ARM_V1, SHUFFLED_FORECAST_ARM_V1):
        comparisons[control] = {}
        for level in arrays:
            candidate = arrays[level][ALIGNED_FORECAST_ARM_V1]
            baseline = arrays[level][control]
            auroc_difference = candidate[2] - baseline[2]
            brier_difference = candidate[3] - baseline[3]
            comparisons[control][level] = {
                "aligned_minus_control_auroc": float(candidate[0] - baseline[0]),
                "aligned_minus_control_auroc_ci95": _interval(auroc_difference),
                "aligned_minus_control_brier": float(candidate[1] - baseline[1]),
                "aligned_minus_control_brier_ci95": _interval(brier_difference),
            }
    return metrics, comparisons


def _prerequisite_components(
    counts: Mapping[str, int],
    labels: Mapping[str, str],
    identities: Mapping[str, tuple[int, str, int]],
    lower_threshold: float,
    upper_threshold: float,
) -> tuple[dict[str, bool], dict[str, int]]:
    test_keys = [
        key
        for key in _registered_player_keys()
        if identities[key][0] in LEARNED_RESOURCE_FORECAST_TEST_SEEDS_V1
    ]
    expert = [key for key in test_keys if labels[key] == "EXPERT"]
    novice = [key for key in test_keys if labels[key] == "NOVICE"]
    expert_clusters = {identities[key][0] for key in expert}
    novice_clusters = {identities[key][0] for key in novice}
    observed = {
        "test_expert_players": len(expert),
        "test_novice_players": len(novice),
        "test_expert_base_seed_clusters": len(expert_clusters),
        "test_novice_base_seed_clusters": len(novice_clusters),
    }
    components = {
        "exact_144_training_jobs_completed": counts["completed_training_jobs"]
        == EXPECTED_TRAINING_JOB_COUNT_V1,
        "no_training_job_failed": counts["failed_training_jobs"] == 0,
        "exact_432_model_snapshots_present": counts["model_snapshots"]
        == EXPECTED_MODEL_SNAPSHOT_COUNT_V1,
        "exact_288_trajectory_player_artifacts_present": counts[
            "trajectory_player_artifacts"
        ]
        == EXPECTED_TRAJECTORY_PLAYER_ARTIFACT_COUNT_V1,
        "exact_4608_complete_trajectory_episodes_present": counts[
            "complete_trajectory_episodes"
        ]
        == EXPECTED_COMPLETE_TRAJECTORY_EPISODE_COUNT_V1,
        "exact_2_forecast_encoder_receipts_present": counts[
            "forecast_encoder_receipts"
        ]
        == EXPECTED_FORECAST_ENCODER_RECEIPT_COUNT_V1,
        "exact_2_frozen_encoder_states_present": counts["frozen_encoder_states"]
        == EXPECTED_FROZEN_ENCODER_STATE_COUNT_V1,
        "exact_432_player_evidence_jobs_completed": counts[
            "completed_player_evidence_jobs"
        ]
        == EXPECTED_PLAYER_COUNT_V1,
        "no_player_evidence_job_failed": counts["failed_player_evidence_jobs"] == 0,
        "exact_432_label_aggregates_present": counts["label_aggregates"]
        == EXPECTED_PLAYER_COUNT_V1,
        "exact_6912_probe_records_present": counts[
            "exact_eight_action_probe_records"
        ]
        == EXPECTED_PROBE_RECORD_COUNT_V1,
        "no_missing_duplicate_or_foreign_identity": all(
            counts[field] == 0
            for field in (
                "missing_identities",
                "duplicate_identities",
                "foreign_identities",
            )
        ),
        "train_inverted_cdf_thresholds_are_distinct": lower_threshold
        < upper_threshold,
        "test_has_at_least_16_expert_players": len(expert) >= 16,
        "test_has_at_least_16_novice_players": len(novice) >= 16,
        "test_has_at_least_8_expert_base_seed_clusters": len(expert_clusters) >= 8,
        "test_has_at_least_8_novice_base_seed_clusters": len(novice_clusters) >= 8,
    }
    return components, observed


def _base_result(
    protocol: Mapping[str, Any],
    counts: Mapping[str, int],
    labels: Mapping[str, str],
    scores: Mapping[str, float],
    identities: Mapping[str, tuple[int, str, int]],
    lower_threshold: float,
    upper_threshold: float,
    prerequisite_components: Mapping[str, bool],
    observed_support: Mapping[str, int],
) -> dict[str, Any]:
    return {
        "schema": LEARNED_RESOURCE_FORECAST_EVALUATION_SCHEMA_V1,
        "protocol_id": protocol["protocol_id"],
        "source_commit": protocol["source_commit"],
        "pilot_execution_identity": protocol["pilot_execution_identity"],
        "skill_thresholds": {
            "method": "INVERTED_CDF_ON_288_TRAIN_PLAYERS",
            "lower_25_percent": lower_threshold,
            "upper_75_percent": upper_threshold,
            "applied_unchanged_to_test": True,
        },
        "policy_labels": [
            {
                "player_key": key,
                "base_seed": identities[key][0],
                "generator_arm": identities[key][1],
                "checkpoint": identities[key][2],
                "split": (
                    "TRAIN"
                    if identities[key][0] in LEARNED_RESOURCE_FORECAST_TRAIN_SEEDS_V1
                    else "TEST"
                ),
                "mean_total_merge_score": scores[key],
                "label": labels[key],
            }
            for key in _registered_player_keys()
        ],
        "prerequisite_counts": dict(counts) | dict(observed_support),
        "prerequisite_components": dict(prerequisite_components),
        "bootstrap": {
            "kind": "PAIRED_TEST_BASE_SEED_CLUSTER_BOOTSTRAP",
            "cluster_count": 16,
            "replicates": BOOTSTRAP_REPLICATES_V1,
            "random_seed": BOOTSTRAP_RANDOM_SEED_V1,
            "confidence_interval": "PERCENTILE_95_LINEAR_QUANTILE",
        },
        "scientific_success": False,
        "scientific_success_claimed": False,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "SCALAR_CALIBRATION_GATE": "NOT_RUN",
        "BREAK_EVEN_GATE": "NOT_RUN",
        "OFFICIAL_EXECUTION_GATE": "NOT_RUN",
        "official_execution_allowed": False,
    }


def evaluate_learned_resource_forecast_pilot_v1(
    protocol: Mapping[str, Any],
    label_aggregates: Sequence[Mapping[str, Any]],
    probe_matrices: Mapping[str, Mapping[str, Any]],
    prerequisite_counts: Mapping[str, Any],
) -> dict[str, Any]:
    """Run the preregistered train/test classifier and six-component pilot Gate."""

    try:
        frozen = _validate_supported_measurement_protocol_v1(protocol)
    except ValueError as error:
        raise LearnedResourceForecastEvaluatorV1Error(str(error)) from error
    if (
        tuple(frozen.get("arms", ())) != LEARNED_RESOURCE_FORECAST_ARMS_V1
        or tuple(frozen.get("representation_arms", ()))
        != PROBE_REPRESENTATION_ARMS_V1
        or frozen.get("representation_dimensions")
        != PROBE_REPRESENTATION_DIMENSIONS_V1
    ):
        _fail("ratified protocol arm or representation registry drifted")
    counts = _validate_prerequisite_counts(prerequisite_counts)
    scores, identities = _validate_label_aggregates(label_aggregates)
    matrices = _validate_probe_matrices(probe_matrices)
    labels, lower_threshold, upper_threshold = assign_skill_labels_v1(
        scores, identities
    )
    prerequisite_components, observed_support = _prerequisite_components(
        counts, labels, identities, lower_threshold, upper_threshold
    )
    result = _base_result(
        frozen,
        counts,
        labels,
        scores,
        identities,
        lower_threshold,
        upper_threshold,
        prerequisite_components,
        observed_support,
    )
    if not all(prerequisite_components.values()):
        components = {
            "aligned_probe_auroc_at_least_0_80": False,
            "aligned_probe_auroc_ci95_lower_at_least_0_75": False,
            "aligned_auroc_delta_ci95_lower_positive_vs_raw": False,
            "aligned_auroc_delta_ci95_lower_positive_vs_shuffled": False,
            "aligned_brier_no_greater_than_both_controls": False,
            "aligned_brier_delta_ci95_upper_at_most_0_01_vs_both_controls": False,
        }
        return result | {
            "test_probe_predictions": [],
            "metrics": None,
            "paired_aligned_comparisons": None,
            "provisional_design_signal_components": components,
            "provisional_design_signal": "FAIL_PREREQUISITE_GATES",
            "PROVISIONAL_DESIGN_SIGNAL_GATE": "FAIL_PREREQUISITE_GATES",
        }

    predictions = _fit_three_classifiers(labels, identities, matrices)
    metrics, comparisons = _metrics_and_comparisons(
        labels, identities, predictions
    )
    candidate = metrics[ALIGNED_FORECAST_ARM_V1]["probe_level"]
    raw_comparison = comparisons[RAW_PREFIX_ARM_V1]["probe_level"]
    shuffled_comparison = comparisons[SHUFFLED_FORECAST_ARM_V1]["probe_level"]
    components = {
        "aligned_probe_auroc_at_least_0_80": candidate["auroc"] >= 0.80,
        "aligned_probe_auroc_ci95_lower_at_least_0_75": candidate["auroc_ci95"][
            "lower"
        ]
        >= 0.75,
        "aligned_auroc_delta_ci95_lower_positive_vs_raw": raw_comparison[
            "aligned_minus_control_auroc_ci95"
        ]["lower"]
        > 0.0,
        "aligned_auroc_delta_ci95_lower_positive_vs_shuffled": shuffled_comparison[
            "aligned_minus_control_auroc_ci95"
        ]["lower"]
        > 0.0,
        "aligned_brier_no_greater_than_both_controls": all(
            candidate["brier"] <= metrics[control]["probe_level"]["brier"]
            for control in (RAW_PREFIX_ARM_V1, SHUFFLED_FORECAST_ARM_V1)
        ),
        "aligned_brier_delta_ci95_upper_at_most_0_01_vs_both_controls": all(
            comparisons[control]["probe_level"][
                "aligned_minus_control_brier_ci95"
            ]["upper"]
            <= 0.01
            for control in (RAW_PREFIX_ARM_V1, SHUFFLED_FORECAST_ARM_V1)
        ),
    }
    signal = "PASS" if all(components.values()) else "FAIL"
    test_keys = [
        key
        for key in _registered_player_keys()
        if identities[key][0] in LEARNED_RESOURCE_FORECAST_TEST_SEEDS_V1
        and labels[key] != "EXCLUDED_MIDDLE"
    ]
    return result | {
        "test_probe_predictions": [
            {
                "player_key": key,
                "base_seed": identities[key][0],
                "label": labels[key],
                "probabilities": {
                    representation: [
                        float(value) for value in predictions[representation][key]
                    ]
                    for representation in PROBE_REPRESENTATION_ARMS_V1
                },
            }
            for key in test_keys
        ],
        "metrics": metrics,
        "paired_aligned_comparisons": comparisons,
        "provisional_design_signal_components": components,
        "provisional_design_signal": signal,
        "PROVISIONAL_DESIGN_SIGNAL_GATE": signal,
    }


__all__ = (
    "LEARNED_RESOURCE_FORECAST_EVALUATION_SCHEMA_V1",
    "LearnedResourceForecastEvaluatorV1Error",
    "assign_skill_labels_v1",
    "brier_score_v1",
    "evaluate_learned_resource_forecast_pilot_v1",
    "tie_safe_auroc_v1",
)
