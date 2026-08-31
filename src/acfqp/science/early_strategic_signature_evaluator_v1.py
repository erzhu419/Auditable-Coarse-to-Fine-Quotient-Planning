"""Grouped evaluator for the candidate-only early-signature pilot."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import math
from typing import Any, NoReturn

import numpy as np
from scipy.optimize import minimize
from scipy.special import expit

from acfqp.science.early_strategic_signature_2048_pilot_v1 import (
    AUGMENTED_PREFIX_DIMENSION_V1,
    RAW_PREFIX_ARM_V1,
    RAW_PREFIX_DIMENSION_V1,
    ROTATED_PREFIX_ARM_V1,
    STRATEGIC_PREFIX_ARM_V1,
)
from acfqp.science.early_strategic_signature_protocol_v1 import (
    BOOTSTRAP_RANDOM_SEED_V1,
    BOOTSTRAP_REPLICATES_V1,
    LABEL_EPISODE_INDICES_V1,
    LOGISTIC_L2_STRENGTH_V1,
    PILOT_ARMS_V1,
    PREFIX_ACTION_COUNT_V1,
    PREFIX_EPISODE_INDICES_V1,
    RAW_ARM_V1,
    ROTATED_REDUNDANCY_ARM_V1,
    STRATEGIC_ARM_V1,
    EarlyStrategicSignatureProtocolV1Error,
    validate_pilot_protocol_v1,
)


WORKER_EVIDENCE_SCHEMA_V1 = (
    "acfqp.science.early_strategic_signature_2048_worker_result.v1"
)
COLLECTOR_EVIDENCE_SCHEMA_V1 = (
    "acfqp.science.early_strategic_signature_2048_pilot_evidence.v1"
)
PILOT_EVALUATION_SCHEMA_V1 = (
    "acfqp.science.early_strategic_signature_evaluation.v1"
)

_WORKER_FIELDS = frozenset(
    {
        "schema",
        "protocol_id",
        "source_commit",
        "pilot_execution_identity",
        "worker",
        "device",
        "execution_id",
        "runtime_context",
        "policy_count",
        "policy_evidence",
        "scientific_success_claimed",
    }
)
_POLICY_FIELDS = frozenset(
    {"seed", "model_filename", "parent_execution_id", "collector"}
)
_COLLECTOR_FIELDS = frozenset(
    {
        "schema",
        "label_tape_root",
        "prefix_tape_root",
        "independent_tape_roots",
        "episode_indices",
        "prefix_accepted_legal_action_count",
        "state_canonicalization_applied",
        "label_rows",
        "prefix_rows",
        "prefix_feature_dimensions",
        "prefix_matrices",
        "strategic_features_use_only_prefix_observations_and_pre_spawn_swipes",
    }
)
_LABEL_ROW_FIELDS = frozenset(
    {
        "episode_index",
        "total_merge_score",
        "maximum_tile_rank",
        "decision_count",
        "terminal_status",
        "won",
    }
)
_PREFIX_ROW_FIELDS = frozenset(
    {"episode_index", "action_indices", "merge_scores", "tape_digests", "final_status"}
)
_RUNTIME_CONTEXT_FIELDS = frozenset(
    {
        "hostname",
        "python_version",
        "numpy_version",
        "scipy_version",
        "torch_version",
        "torch_cuda_runtime_version",
        "torch_cudnn_version",
        "device",
        "cuda_device_name",
    }
)
_COLLECTOR_ARM_BY_PILOT_ARM = {
    RAW_ARM_V1: RAW_PREFIX_ARM_V1,
    ROTATED_REDUNDANCY_ARM_V1: ROTATED_PREFIX_ARM_V1,
    STRATEGIC_ARM_V1: STRATEGIC_PREFIX_ARM_V1,
}
_EXPECTED_DIMENSIONS = {
    RAW_PREFIX_ARM_V1: RAW_PREFIX_DIMENSION_V1,
    ROTATED_PREFIX_ARM_V1: AUGMENTED_PREFIX_DIMENSION_V1,
    STRATEGIC_PREFIX_ARM_V1: AUGMENTED_PREFIX_DIMENSION_V1,
}


class EarlyStrategicSignatureEvaluatorV1Error(ValueError):
    """The pilot evidence or fixed grouped analysis is invalid."""


def _fail(message: str) -> NoReturn:
    raise EarlyStrategicSignatureEvaluatorV1Error(message)


def _finite_number(value: Any) -> bool:
    return type(value) in (int, float) and math.isfinite(float(value))


def assign_policy_labels_v1(
    mean_label_scores: Mapping[int, float],
) -> dict[int, str]:
    """Assign bottom/top octiles with ascending seed as the fixed tie break."""

    if (
        not isinstance(mean_label_scores, Mapping)
        or len(mean_label_scores) != 24
        or any(type(seed) is not int for seed in mean_label_scores)
        or any(not _finite_number(score) for score in mean_label_scores.values())
    ):
        _fail("policy label scores must be 24 finite seed-indexed means")
    ranked = sorted(
        mean_label_scores,
        key=lambda seed: (float(mean_label_scores[seed]), seed),
    )
    result = {seed: "EXCLUDED_MIDDLE" for seed in ranked}
    for seed in ranked[:8]:
        result[seed] = "NOVICE"
    for seed in ranked[-8:]:
        result[seed] = "EXPERT"
    return result


def tie_safe_auroc_v1(labels: Sequence[int], scores: Sequence[float]) -> float:
    """Return rank AUROC with average ranks for every score tie."""

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
    positive_count = int(np.sum(y == 1))
    negative_count = int(np.sum(y == 0))
    if positive_count == 0 or negative_count == 0:
        _fail("AUROC requires both policy labels")

    order = np.argsort(values, kind="mergesort")
    ranks = np.empty(len(values), dtype=np.float64)
    start = 0
    while start < len(values):
        stop = start + 1
        while stop < len(values) and values[order[stop]] == values[order[start]]:
            stop += 1
        ranks[order[start:stop]] = ((start + 1) + stop) / 2.0
        start = stop
    positive_rank_sum = float(np.sum(ranks[y == 1]))
    return (
        positive_rank_sum - positive_count * (positive_count + 1) / 2.0
    ) / (positive_count * negative_count)


def brier_score_v1(labels: Sequence[int], probabilities: Sequence[float]) -> float:
    """Return the binary Brier score for fixed held-out predictions."""

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


def _validate_label_rows(value: Any) -> list[dict[str, Any]]:
    if (
        type(value) is not list
        or len(value) != 64
        or any(type(row) is not dict or set(row) != _LABEL_ROW_FIELDS for row in value)
    ):
        _fail("collector label_rows must contain the exact 64 full episodes")
    rows = [dict(row) for row in value]
    if [row["episode_index"] for row in rows] != list(LABEL_EPISODE_INDICES_V1):
        _fail("collector label episode registry changed")
    for row in rows:
        if (
            not _finite_number(row["total_merge_score"])
            or float(row["total_merge_score"]) < 0
            or type(row["maximum_tile_rank"]) is not int
            or row["maximum_tile_rank"] < 0
            or type(row["decision_count"]) is not int
            or row["decision_count"] <= 0
            or row["terminal_status"] not in {"WON", "LOST"}
            or type(row["won"]) is not bool
            or row["won"] != (row["terminal_status"] == "WON")
        ):
            _fail("collector label row is not one completed finite episode")
    return rows


def _validate_prefix_rows(value: Any) -> list[dict[str, Any]]:
    if (
        type(value) is not list
        or len(value) != 64
        or any(type(row) is not dict or set(row) != _PREFIX_ROW_FIELDS for row in value)
    ):
        _fail("collector prefix_rows must contain the exact 64 prefixes")
    rows = [dict(row) for row in value]
    if [row["episode_index"] for row in rows] != list(PREFIX_EPISODE_INDICES_V1):
        _fail("collector prefix episode registry changed")
    for row in rows:
        actions = row["action_indices"]
        merge_scores = row["merge_scores"]
        tape_digests = row["tape_digests"]
        if (
            type(actions) is not list
            or len(actions) != PREFIX_ACTION_COUNT_V1
            or any(type(action) is not int or not 0 <= action < 4 for action in actions)
            or type(merge_scores) is not list
            or len(merge_scores) != PREFIX_ACTION_COUNT_V1
            or any(type(score) is not int or score < 0 for score in merge_scores)
            or type(tape_digests) is not list
            or len(tape_digests) != PREFIX_ACTION_COUNT_V1
            or any(
                type(digest) is not str or len(digest) != 64
                for digest in tape_digests
            )
            or row["final_status"] not in {"ACTIVE", "WON", "LOST"}
        ):
            _fail("collector prefix is not exactly eight legal accepted actions")
    return rows


def _validate_matrix(value: Any, dimension: int) -> np.ndarray:
    if type(value) is not list or len(value) != 64:
        _fail("collector prefix matrix must have exactly 64 rows")
    if any(type(row) is not list or len(row) != dimension for row in value):
        _fail("collector prefix feature dimension changed")
    try:
        matrix = np.asarray(value, dtype=np.float64)
    except (TypeError, ValueError) as error:
        raise EarlyStrategicSignatureEvaluatorV1Error(
            "collector prefix matrix is not numeric"
        ) from error
    if matrix.shape != (64, dimension) or not np.all(np.isfinite(matrix)):
        _fail("collector prefix matrix contains a non-finite value")
    return matrix


def _validate_collector(
    collector: Any, protocol: Mapping[str, Any]
) -> tuple[float, dict[str, np.ndarray]]:
    if type(collector) is not dict or set(collector) != _COLLECTOR_FIELDS:
        _fail("collector payload field set changed")
    if (
        collector["schema"] != COLLECTOR_EVIDENCE_SCHEMA_V1
        or collector["label_tape_root"] != protocol["label_tape_root"]
        or collector["prefix_tape_root"] != protocol["prefix_tape_root"]
        or collector["label_tape_root"] == collector["prefix_tape_root"]
        or collector["independent_tape_roots"] is not True
        or collector["episode_indices"] != list(LABEL_EPISODE_INDICES_V1)
        or collector["episode_indices"] != list(PREFIX_EPISODE_INDICES_V1)
        or collector["prefix_accepted_legal_action_count"] != PREFIX_ACTION_COUNT_V1
        or collector["state_canonicalization_applied"] is not False
        or collector[
            "strategic_features_use_only_prefix_observations_and_pre_spawn_swipes"
        ]
        is not True
        or collector["prefix_feature_dimensions"] != _EXPECTED_DIMENSIONS
        or type(collector["prefix_matrices"]) is not dict
        or set(collector["prefix_matrices"]) != set(_EXPECTED_DIMENSIONS)
    ):
        _fail("collector payload does not match the frozen tapes/features")
    label_rows = _validate_label_rows(collector["label_rows"])
    _validate_prefix_rows(collector["prefix_rows"])
    matrices = {
        pilot_arm: _validate_matrix(
            collector["prefix_matrices"][collector_arm],
            _EXPECTED_DIMENSIONS[collector_arm],
        )
        for pilot_arm, collector_arm in _COLLECTOR_ARM_BY_PILOT_ARM.items()
    }
    mean_label_score = float(
        np.mean([float(row["total_merge_score"]) for row in label_rows])
    )
    return mean_label_score, matrices


def _validated_policy_evidence(
    protocol: Mapping[str, Any], worker_documents: Sequence[Mapping[str, Any]]
) -> tuple[dict[int, float], dict[str, dict[int, np.ndarray]]]:
    if (
        not isinstance(worker_documents, Sequence)
        or isinstance(worker_documents, (str, bytes))
        or len(worker_documents) != 2
        or any(type(document) is not dict for document in worker_documents)
    ):
        _fail("exactly two worker evidence documents are required")
    documents = sorted(
        worker_documents, key=lambda document: document.get("worker", -1)
    )
    if [document.get("worker") for document in documents] != [0, 1]:
        _fail("worker evidence must close workers 0 and 1")

    roster = protocol["candidate_models"]
    mean_scores: dict[int, float] = {}
    matrices: dict[str, dict[int, np.ndarray]] = {arm: {} for arm in PILOT_ARMS_V1}
    shared_runtime_context: dict[str, Any] | None = None
    for worker, document in enumerate(documents):
        if set(document) != _WORKER_FIELDS:
            _fail("worker evidence field set changed")
        expected_rows = [row for row in roster if row["worker"] == worker]
        rows = document["policy_evidence"]
        runtime_context = document["runtime_context"]
        if (
            document["schema"] != WORKER_EVIDENCE_SCHEMA_V1
            or document["protocol_id"] != protocol["protocol_id"]
            or document["source_commit"] != protocol["source_commit"]
            or document["pilot_execution_identity"]
            != protocol["pilot_execution_identity"]
            or document["worker"] != worker
            or document["device"] != f"cuda:{worker}"
            or document["execution_id"]
            != f"{protocol['pilot_execution_identity']}:worker:{worker}"
            or type(runtime_context) is not dict
            or set(runtime_context) != _RUNTIME_CONTEXT_FIELDS
            or runtime_context["device"] != f"cuda:{worker}"
            or any(
                type(runtime_context[field]) is not str
                or not runtime_context[field]
                for field in (
                    "hostname",
                    "python_version",
                    "numpy_version",
                    "scipy_version",
                    "torch_version",
                    "cuda_device_name",
                )
            )
            or (
                runtime_context["torch_cuda_runtime_version"] is not None
                and type(runtime_context["torch_cuda_runtime_version"]) is not str
            )
            or (
                runtime_context["torch_cudnn_version"] is not None
                and type(runtime_context["torch_cudnn_version"]) is not int
            )
            or document["policy_count"] != 12
            or document["scientific_success_claimed"] is not False
            or type(rows) is not list
            or len(rows) != 12
            or any(type(row) is not dict or set(row) != _POLICY_FIELDS for row in rows)
        ):
            _fail("worker evidence identity or 12-policy shape changed")
        comparable_runtime_context = {
            key: value
            for key, value in runtime_context.items()
            if key not in {"device", "cuda_device_name"}
        }
        if shared_runtime_context is None:
            shared_runtime_context = comparable_runtime_context
        elif comparable_runtime_context != shared_runtime_context:
            _fail("worker runtime contexts differ beyond CUDA device identity")
        for row, expected in zip(rows, expected_rows, strict=True):
            if (
                row["seed"],
                row["model_filename"],
                row["parent_execution_id"],
            ) != (
                expected["seed"],
                expected["model_filename"],
                expected["parent_execution_id"],
            ):
                _fail("worker policy evidence differs from the frozen roster")
            seed = row["seed"]
            mean_score, policy_matrices = _validate_collector(
                row["collector"], protocol
            )
            if seed in mean_scores:
                _fail("worker evidence repeats a policy seed")
            mean_scores[seed] = mean_score
            for arm in PILOT_ARMS_V1:
                matrices[arm][seed] = policy_matrices[arm]
    if set(mean_scores) != {row["seed"] for row in roster}:
        _fail("worker evidence does not close the exact 24 candidate policies")
    return mean_scores, matrices


def _fit_fold_probabilities(
    training_features: np.ndarray,
    training_labels: np.ndarray,
    heldout_features: np.ndarray,
) -> np.ndarray:
    means = np.mean(training_features, axis=0)
    scales = np.std(training_features, axis=0, ddof=0)
    scales = np.where(scales == 0, 1.0, scales)
    x_train = (training_features - means) / scales
    x_heldout = (heldout_features - means) / scales
    labels = training_labels.astype(np.float64)
    negative_count = int(np.sum(labels == 0))
    positive_count = int(np.sum(labels == 1))
    if negative_count == 0 or positive_count == 0:
        _fail("each logistic training fold must contain both policy labels")
    sample_weights = np.where(
        labels == 0,
        0.5 / negative_count,
        0.5 / positive_count,
    )

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
    probabilities = expit(x_heldout @ fit.x[:-1] + fit.x[-1])
    if probabilities.shape != (64,) or not np.all(np.isfinite(probabilities)):
        _fail("held-out probability shape changed")
    return probabilities


def _grouped_predictions(
    labels: Mapping[int, str], matrices: Mapping[str, Mapping[int, np.ndarray]]
) -> dict[str, dict[int, np.ndarray]]:
    included = sorted(
        seed for seed, label in labels.items() if label != "EXCLUDED_MIDDLE"
    )
    numeric_label = {seed: int(labels[seed] == "EXPERT") for seed in included}
    predictions: dict[str, dict[int, np.ndarray]] = {arm: {} for arm in PILOT_ARMS_V1}
    for arm in PILOT_ARMS_V1:
        for heldout_seed in included:
            training_seeds = [seed for seed in included if seed != heldout_seed]
            training_features = np.concatenate(
                [matrices[arm][seed] for seed in training_seeds], axis=0
            )
            training_labels = np.concatenate(
                [
                    np.full(64, numeric_label[seed], dtype=np.int64)
                    for seed in training_seeds
                ]
            )
            predictions[arm][heldout_seed] = _fit_fold_probabilities(
                training_features,
                training_labels,
                matrices[arm][heldout_seed],
            )
    return predictions


def _metric_pair(
    seeds: Sequence[int],
    numeric_labels: Mapping[int, int],
    probabilities: Mapping[int, np.ndarray],
) -> tuple[float, float]:
    labels = np.concatenate(
        [np.full(64, numeric_labels[seed], dtype=np.int64) for seed in seeds]
    )
    scores = np.concatenate([probabilities[seed] for seed in seeds])
    return tie_safe_auroc_v1(labels, scores), brier_score_v1(labels, scores)


def _interval(values: np.ndarray) -> dict[str, float]:
    lower, upper = np.quantile(values, (0.025, 0.975), method="linear")
    return {"lower": float(lower), "upper": float(upper)}


def _bootstrap(
    labels: Mapping[int, str], predictions: Mapping[str, Mapping[int, np.ndarray]]
) -> tuple[
    dict[str, dict[str, Any]],
    dict[str, dict[str, Any]],
]:
    novice = np.asarray(
        sorted(seed for seed, label in labels.items() if label == "NOVICE")
    )
    expert = np.asarray(
        sorted(seed for seed, label in labels.items() if label == "EXPERT")
    )
    numeric_labels = {int(seed): 0 for seed in novice} | {
        int(seed): 1 for seed in expert
    }
    included = [int(seed) for seed in novice] + [int(seed) for seed in expert]
    point = {
        arm: _metric_pair(included, numeric_labels, predictions[arm])
        for arm in PILOT_ARMS_V1
    }
    bootstrap_auroc = {
        arm: np.empty(BOOTSTRAP_REPLICATES_V1, dtype=np.float64)
        for arm in PILOT_ARMS_V1
    }
    bootstrap_brier = {
        arm: np.empty(BOOTSTRAP_REPLICATES_V1, dtype=np.float64)
        for arm in PILOT_ARMS_V1
    }
    generator = np.random.default_rng(BOOTSTRAP_RANDOM_SEED_V1)
    for replicate in range(BOOTSTRAP_REPLICATES_V1):
        sampled = np.concatenate(
            (
                generator.choice(novice, size=8, replace=True),
                generator.choice(expert, size=8, replace=True),
            )
        ).tolist()
        for arm in PILOT_ARMS_V1:
            auroc, brier = _metric_pair(sampled, numeric_labels, predictions[arm])
            bootstrap_auroc[arm][replicate] = auroc
            bootstrap_brier[arm][replicate] = brier

    metrics = {
        arm: {
            "auroc": float(point[arm][0]),
            "auroc_ci95": _interval(bootstrap_auroc[arm]),
            "brier": float(point[arm][1]),
            "brier_ci95": _interval(bootstrap_brier[arm]),
        }
        for arm in PILOT_ARMS_V1
    }
    comparisons = {}
    for control in (RAW_ARM_V1, ROTATED_REDUNDANCY_ARM_V1):
        comparisons[control] = {
            "strategic_minus_control_auroc": float(
                point[STRATEGIC_ARM_V1][0] - point[control][0]
            ),
            "strategic_minus_control_auroc_ci95": _interval(
                bootstrap_auroc[STRATEGIC_ARM_V1] - bootstrap_auroc[control]
            ),
            "strategic_minus_control_brier": float(
                point[STRATEGIC_ARM_V1][1] - point[control][1]
            ),
            "strategic_minus_control_brier_ci95": _interval(
                bootstrap_brier[STRATEGIC_ARM_V1] - bootstrap_brier[control]
            ),
        }
    return metrics, comparisons


def evaluate_pilot_v1(
    protocol: Mapping[str, Any], worker_documents: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    """Validate two workers and run the frozen grouped feasibility analysis."""

    try:
        frozen_protocol = validate_pilot_protocol_v1(protocol)
    except EarlyStrategicSignatureProtocolV1Error as error:
        raise EarlyStrategicSignatureEvaluatorV1Error(str(error)) from error
    mean_scores, matrices = _validated_policy_evidence(
        frozen_protocol, worker_documents
    )
    labels = assign_policy_labels_v1(mean_scores)
    predictions = _grouped_predictions(labels, matrices)
    metrics, comparisons = _bootstrap(labels, predictions)

    components = {
        "strategic_auroc_at_least_0_80": metrics[STRATEGIC_ARM_V1]["auroc"] >= 0.80,
        "strategic_auroc_ci95_lower_at_least_0_75": metrics[STRATEGIC_ARM_V1][
            "auroc_ci95"
        ]["lower"]
        >= 0.75,
        "strategic_auroc_delta_ci95_lower_positive_vs_raw": comparisons[RAW_ARM_V1][
            "strategic_minus_control_auroc_ci95"
        ]["lower"]
        > 0,
        "strategic_auroc_delta_ci95_lower_positive_vs_rotated": comparisons[
            ROTATED_REDUNDANCY_ARM_V1
        ]["strategic_minus_control_auroc_ci95"]["lower"]
        > 0,
        "strategic_brier_delta_ci95_upper_nonpositive_vs_raw": comparisons[RAW_ARM_V1][
            "strategic_minus_control_brier_ci95"
        ]["upper"]
        <= 0,
        "strategic_brier_delta_ci95_upper_nonpositive_vs_rotated": comparisons[
            ROTATED_REDUNDANCY_ARM_V1
        ]["strategic_minus_control_brier_ci95"]["upper"]
        <= 0,
    }
    design_signal = "PASS" if all(components.values()) else "FAIL"
    included_seeds = sorted(
        seed for seed, label in labels.items() if label != "EXCLUDED_MIDDLE"
    )
    return {
        "schema": PILOT_EVALUATION_SCHEMA_V1,
        "protocol_id": frozen_protocol["protocol_id"],
        "source_commit": frozen_protocol["source_commit"],
        "pilot_execution_identity": frozen_protocol["pilot_execution_identity"],
        "policy_seed_is_statistical_cluster": True,
        "policy_labels": [
            {
                "seed": seed,
                "mean_label_score": float(mean_scores[seed]),
                "label": labels[seed],
            }
            for seed in sorted(labels)
        ],
        "leave_one_policy_out_predictions": [
            {
                "seed": seed,
                "label": labels[seed],
                "episode_indices": list(PREFIX_EPISODE_INDICES_V1),
                "probabilities": {
                    arm: [float(value) for value in predictions[arm][seed]]
                    for arm in PILOT_ARMS_V1
                },
            }
            for seed in included_seeds
        ],
        "metrics": metrics,
        "paired_strategic_comparisons": comparisons,
        "bootstrap": {
            "kind": "PAIRED_STRATIFIED_POLICY_CLUSTER_BOOTSTRAP",
            "replicates": BOOTSTRAP_REPLICATES_V1,
            "random_seed": BOOTSTRAP_RANDOM_SEED_V1,
            "confidence_interval": "PERCENTILE_95",
        },
        "provisional_design_signal_components": components,
        "provisional_design_signal": design_signal,
        "PROVISIONAL_DESIGN_SIGNAL_GATE": design_signal,
        "scientific_success": False,
        "scientific_success_claimed": False,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "SCALAR_CALIBRATION_GATE": "NOT_RUN",
        "BREAK_EVEN_GATE": "NOT_RUN",
        "OFFICIAL_EXECUTION_GATE": "NOT_RUN",
        "official_execution_allowed": False,
    }


__all__ = (
    "COLLECTOR_EVIDENCE_SCHEMA_V1",
    "EarlyStrategicSignatureEvaluatorV1Error",
    "PILOT_EVALUATION_SCHEMA_V1",
    "WORKER_EVIDENCE_SCHEMA_V1",
    "assign_policy_labels_v1",
    "brier_score_v1",
    "evaluate_pilot_v1",
    "tie_safe_auroc_v1",
)
