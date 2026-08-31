"""Grouped evaluator for the frozen 2048 decision-point signature pilot."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import math
from typing import Any, NoReturn

import numpy as np
from scipy.optimize import minimize
from scipy.special import expit

from acfqp.science.decision_point_signature_2048_pilot_v2 import (
    AUGMENTED_PREFIX_DIMENSION_V2,
    DECISION_PREFIX_ACTION_COUNT_V2,
    DECISION_STATE_COUNT_V2,
    RAW_PREFIX_ARM_V2,
    RAW_PREFIX_DIMENSION_V2,
    ROTATED_PREFIX_ARM_V2,
    STRATEGIC_PREFIX_ARM_V2,
)
from acfqp.science.decision_point_signature_protocol_v2 import (
    BOOTSTRAP_REPLICATES_V2,
    DecisionPointSignatureProtocolV2Error,
    LOGISTIC_L2_STRENGTH_V2,
    PILOT_ARMS_V2,
    RAW_ARM_V2,
    ROTATED_REDUNDANCY_ARM_V2,
    STRATEGIC_ARM_V2,
    validate_decision_point_protocol_v2,
)


WORKER_EVIDENCE_SCHEMA_V2 = (
    "acfqp.science.decision_point_signature_2048_worker_result.v2"
)
COLLECTOR_EVIDENCE_SCHEMA_V2 = (
    "acfqp.science.decision_point_signature_2048_pilot_evidence.v2"
)
PILOT_EVALUATION_SCHEMA_V2 = (
    "acfqp.science.decision_point_signature_evaluation.v2"
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
        "state_library_tape_root",
        "prefix_tape_root",
        "state_count",
        "state_indices",
        "prefix_accepted_legal_action_count",
        "state_canonicalization_applied",
        "label_lane_present",
        "decision_state_rows",
        "prefix_rows",
        "prefix_feature_dimensions",
        "prefix_matrices",
        "strategic_features_use_only_observed_prefix_and_pre_spawn_swipes",
        "independent_state_generation_and_policy_execution",
    }
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
_PREFIX_ROW_FIELDS = frozenset(
    {
        "state_index",
        "generator_episode_index",
        "generator_decision_index",
        "action_indices",
        "merge_scores",
        "tape_digests",
        "final_status",
    }
)
_EXPECTED_DIMENSIONS = {
    RAW_PREFIX_ARM_V2: RAW_PREFIX_DIMENSION_V2,
    ROTATED_PREFIX_ARM_V2: AUGMENTED_PREFIX_DIMENSION_V2,
    STRATEGIC_PREFIX_ARM_V2: AUGMENTED_PREFIX_DIMENSION_V2,
}
_PILOT_ARMS = PILOT_ARMS_V2
_RAW_ARM = RAW_ARM_V2
_ROTATED_ARM = ROTATED_REDUNDANCY_ARM_V2
_STRATEGIC_ARM = STRATEGIC_ARM_V2
_FEATURE_KEY_BY_ARM = {
    _RAW_ARM: RAW_PREFIX_ARM_V2,
    _ROTATED_ARM: ROTATED_PREFIX_ARM_V2,
    _STRATEGIC_ARM: STRATEGIC_PREFIX_ARM_V2,
}
_L2_STRENGTH = LOGISTIC_L2_STRENGTH_V2
_BOOTSTRAP_REPLICATES = BOOTSTRAP_REPLICATES_V2


class DecisionPointSignatureEvaluatorV2Error(ValueError):
    """The protocol, worker evidence, or frozen grouped analysis is invalid."""


def _fail(message: str) -> NoReturn:
    raise DecisionPointSignatureEvaluatorV2Error(message)


def _finite_number(value: Any) -> bool:
    return type(value) in (int, float) and math.isfinite(float(value))


def tie_safe_auroc_v2(labels: Sequence[int], scores: Sequence[float]) -> float:
    """Return rank AUROC with average ranks for exact score ties."""

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


def brier_score_v2(labels: Sequence[int], probabilities: Sequence[float]) -> float:
    """Return the binary Brier score for fixed held-out probabilities."""

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


def _protocol_labels(protocol: Mapping[str, Any]) -> dict[int, str]:
    rows = protocol.get("policy_labels")
    if type(rows) is not list or len(rows) != 24 or any(type(row) is not dict for row in rows):
        _fail("protocol must freeze exactly 24 policy labels")
    labels: dict[int, str] = {}
    for row in rows:
        if set(row) != {"seed", "mean_label_score", "label"}:
            _fail("protocol policy-label field set changed")
        seed = row["seed"]
        if (
            type(seed) is not int
            or seed in labels
            or not _finite_number(row["mean_label_score"])
            or row["label"] not in {"NOVICE", "EXCLUDED_MIDDLE", "EXPERT"}
        ):
            _fail("protocol policy labels are malformed")
        labels[seed] = row["label"]
    roster_seeds = {row.get("seed") for row in protocol.get("candidate_models", [])}
    if set(labels) != roster_seeds:
        _fail("protocol labels differ from the fixed candidate roster")
    if [sum(label == name for label in labels.values()) for name in ("NOVICE", "EXCLUDED_MIDDLE", "EXPERT")] != [8, 8, 8]:
        _fail("protocol must freeze eight novice, middle, and expert policies")
    return labels


def _validate_matrix(value: Any, dimension: int) -> np.ndarray:
    if type(value) is not list or len(value) != DECISION_STATE_COUNT_V2:
        _fail("collector prefix matrix must have exactly 64 decision rows")
    if any(type(row) is not list or len(row) != dimension for row in value):
        _fail("collector decision-prefix feature dimension changed")
    try:
        matrix = np.asarray(value, dtype=np.float64)
    except (TypeError, ValueError) as error:
        raise DecisionPointSignatureEvaluatorV2Error(
            "collector decision-prefix matrix is not numeric"
        ) from error
    if matrix.shape != (DECISION_STATE_COUNT_V2, dimension) or not np.all(np.isfinite(matrix)):
        _fail("collector decision-prefix matrix contains a non-finite value")
    return matrix


def _validate_prefix_rows(
    value: Any, expected_states: Sequence[Mapping[str, Any]]
) -> None:
    if (
        type(value) is not list
        or len(value) != DECISION_STATE_COUNT_V2
        or any(type(row) is not dict or set(row) != _PREFIX_ROW_FIELDS for row in value)
    ):
        _fail("collector prefix_rows must contain the exact 64 decision prefixes")
    if [row.get("state_index") for row in value] != list(range(DECISION_STATE_COUNT_V2)):
        _fail("collector decision-prefix state registry changed")
    for row, expected_state in zip(value, expected_states, strict=True):
        actions = row.get("action_indices")
        merge_scores = row.get("merge_scores")
        tape_digests = row.get("tape_digests")
        if (
            type(row["generator_episode_index"]) is not int
            or row["generator_episode_index"] < 0
            or type(row["generator_decision_index"]) is not int
            or row["generator_decision_index"] <= 0
            or row["generator_episode_index"]
            != expected_state["generator_episode_index"]
            or row["generator_decision_index"]
            != expected_state["generator_decision_index"]
            or type(actions) is not list
            or len(actions) != DECISION_PREFIX_ACTION_COUNT_V2
            or any(type(action) is not int or not 0 <= action < 4 for action in actions)
            or type(merge_scores) is not list
            or len(merge_scores) != DECISION_PREFIX_ACTION_COUNT_V2
            or any(type(score) is not int or score < 0 for score in merge_scores)
            or type(tape_digests) is not list
            or len(tape_digests) != DECISION_PREFIX_ACTION_COUNT_V2
            or any(type(digest) is not str or len(digest) != 64 for digest in tape_digests)
            or row.get("final_status") not in {"ACTIVE", "WON", "LOST"}
        ):
            _fail("collector row is not exactly eight accepted legal actions")


def _validate_collector(
    collector: Any, protocol: Mapping[str, Any]
) -> dict[str, np.ndarray]:
    if type(collector) is not dict or set(collector) != _COLLECTOR_FIELDS:
        _fail("collector payload field set changed")
    expected_states = protocol["decision_states"]
    expected_indices = list(range(DECISION_STATE_COUNT_V2))
    if (
        collector["schema"] != COLLECTOR_EVIDENCE_SCHEMA_V2
        or collector["state_library_tape_root"]
        != protocol["decision_state_library_contract"]["tape_root"]
        or collector["prefix_tape_root"] != protocol["prefix_tape_root"]
        or collector["state_count"] != DECISION_STATE_COUNT_V2
        or collector["state_indices"] != expected_indices
        or collector["prefix_accepted_legal_action_count"] != DECISION_PREFIX_ACTION_COUNT_V2
        or collector["state_canonicalization_applied"] is not False
        or collector["label_lane_present"] is not False
        or collector["decision_state_rows"] != expected_states
        or collector["prefix_feature_dimensions"] != _EXPECTED_DIMENSIONS
        or type(collector["prefix_matrices"]) is not dict
        or set(collector["prefix_matrices"]) != set(_EXPECTED_DIMENSIONS)
        or collector["strategic_features_use_only_observed_prefix_and_pre_spawn_swipes"] is not True
        or collector["independent_state_generation_and_policy_execution"] is not True
    ):
        _fail("collector payload does not match the frozen decision states/features")
    _validate_prefix_rows(collector["prefix_rows"], expected_states)
    return {
        arm: _validate_matrix(
            collector["prefix_matrices"][feature_key],
            _EXPECTED_DIMENSIONS[feature_key],
        )
        for arm, feature_key in _FEATURE_KEY_BY_ARM.items()
    }


def _validated_policy_evidence(
    protocol: Mapping[str, Any], worker_documents: Sequence[Mapping[str, Any]]
) -> dict[str, dict[int, np.ndarray]]:
    if (
        not isinstance(worker_documents, Sequence)
        or isinstance(worker_documents, (str, bytes))
        or len(worker_documents) != 2
        or any(type(document) is not dict for document in worker_documents)
    ):
        _fail("exactly two worker evidence documents are required")
    documents = sorted(worker_documents, key=lambda document: document.get("worker", -1))
    if [document.get("worker") for document in documents] != [0, 1]:
        _fail("worker evidence must close workers 0 and 1")
    roster = protocol["candidate_models"]
    matrices: dict[str, dict[int, np.ndarray]] = {arm: {} for arm in _PILOT_ARMS}
    shared_runtime_context: dict[str, Any] | None = None
    for worker, document in enumerate(documents):
        expected_rows = [row for row in roster if row["worker"] == worker]
        rows = document.get("policy_evidence")
        runtime_context = document.get("runtime_context")
        if (
            set(document) != _WORKER_FIELDS
            or document["schema"] != WORKER_EVIDENCE_SCHEMA_V2
            or document["protocol_id"] != protocol["protocol_id"]
            or document["source_commit"] != protocol["source_commit"]
            or document["pilot_execution_identity"] != protocol["pilot_execution_identity"]
            or document["worker"] != worker
            or document["device"] != f"cuda:{worker}"
            or document["execution_id"] != f"{protocol['pilot_execution_identity']}:worker:{worker}"
            or type(runtime_context) is not dict
            or set(runtime_context) != _RUNTIME_CONTEXT_FIELDS
            or any(
                type(runtime_context[field]) is not str
                or not runtime_context[field]
                for field in (
                    "hostname",
                    "python_version",
                    "numpy_version",
                    "scipy_version",
                    "torch_version",
                    "device",
                    "cuda_device_name",
                )
            )
            or (
                runtime_context["torch_cuda_runtime_version"] is not None
                and (
                    type(runtime_context["torch_cuda_runtime_version"]) is not str
                    or not runtime_context["torch_cuda_runtime_version"]
                )
            )
            or (
                runtime_context["torch_cudnn_version"] is not None
                and type(runtime_context["torch_cudnn_version"]) is not int
            )
            or runtime_context["device"] != f"cuda:{worker}"
            or document["policy_count"] != 12
            or document["scientific_success_claimed"] is not False
            or type(rows) is not list
            or len(rows) != 12
            or any(type(row) is not dict or set(row) != _POLICY_FIELDS for row in rows)
        ):
            _fail("worker evidence identity, runtime, or 12-policy shape changed")
        comparable = {key: value for key, value in runtime_context.items() if key not in {"device", "cuda_device_name"}}
        if shared_runtime_context is None:
            shared_runtime_context = comparable
        elif comparable != shared_runtime_context:
            _fail("worker runtime contexts differ beyond CUDA device identity")
        for row, expected in zip(rows, expected_rows, strict=True):
            if (row["seed"], row["model_filename"], row["parent_execution_id"]) != (
                expected["seed"], expected["model_filename"], expected["parent_execution_id"]
            ):
                _fail("worker policy evidence differs from the frozen roster")
            seed = row["seed"]
            if any(seed in matrices[arm] for arm in _PILOT_ARMS):
                _fail("worker evidence repeats a policy seed")
            policy_matrices = _validate_collector(row["collector"], protocol)
            for arm in _PILOT_ARMS:
                matrices[arm][seed] = policy_matrices[arm]
    expected_seeds = {row["seed"] for row in roster}
    if any(set(matrices[arm]) != expected_seeds for arm in _PILOT_ARMS):
        _fail("worker evidence does not close the exact 24 candidate policies")
    return matrices


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
    sample_weights = np.where(labels == 0, 0.5 / negative_count, 0.5 / positive_count)

    def objective(parameters: np.ndarray) -> tuple[float, np.ndarray]:
        weights = parameters[:-1]
        intercept = parameters[-1]
        logits = x_train @ weights + intercept
        loss = float(
            np.sum(sample_weights * (np.logaddexp(0.0, logits) - labels * logits))
            + 0.5 * _L2_STRENGTH * np.dot(weights, weights)
        )
        residual = sample_weights * (expit(logits) - labels)
        gradient = np.concatenate(
            (x_train.T @ residual + _L2_STRENGTH * weights, np.asarray([np.sum(residual)]))
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
    if probabilities.shape != (DECISION_STATE_COUNT_V2,) or not np.all(np.isfinite(probabilities)):
        _fail("held-out probability shape changed")
    return probabilities


def _grouped_predictions(
    labels: Mapping[int, str], matrices: Mapping[str, Mapping[int, np.ndarray]]
) -> dict[str, dict[int, np.ndarray]]:
    included = sorted(seed for seed, label in labels.items() if label != "EXCLUDED_MIDDLE")
    numeric = {seed: int(labels[seed] == "EXPERT") for seed in included}
    predictions: dict[str, dict[int, np.ndarray]] = {arm: {} for arm in _PILOT_ARMS}
    for arm in _PILOT_ARMS:
        for heldout_seed in included:
            training_seeds = [seed for seed in included if seed != heldout_seed]
            training_features = np.concatenate([matrices[arm][seed] for seed in training_seeds], axis=0)
            training_labels = np.concatenate(
                [np.full(DECISION_STATE_COUNT_V2, numeric[seed], dtype=np.int64) for seed in training_seeds]
            )
            predictions[arm][heldout_seed] = _fit_fold_probabilities(
                training_features, training_labels, matrices[arm][heldout_seed]
            )
    return predictions


def _metric_pair(
    seeds: Sequence[int],
    numeric_labels: Mapping[int, int],
    probabilities: Mapping[int, np.ndarray],
) -> tuple[float, float]:
    labels = np.concatenate(
        [np.full(DECISION_STATE_COUNT_V2, numeric_labels[seed], dtype=np.int64) for seed in seeds]
    )
    scores = np.concatenate([probabilities[seed] for seed in seeds])
    return tie_safe_auroc_v2(labels, scores), brier_score_v2(labels, scores)


def _interval(values: np.ndarray) -> dict[str, float]:
    lower, upper = np.quantile(values, (0.025, 0.975), method="linear")
    return {"lower": float(lower), "upper": float(upper)}


def _bootstrap(
    protocol: Mapping[str, Any],
    labels: Mapping[int, str],
    predictions: Mapping[str, Mapping[int, np.ndarray]],
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]], int]:
    contract = protocol["bootstrap_contract"]
    random_seed = contract["random_seed"]
    if (
        contract.get("kind") != "PAIRED_STRATIFIED_POLICY_CLUSTER_BOOTSTRAP"
        or contract.get("replicates") != _BOOTSTRAP_REPLICATES
        or type(random_seed) is not int
        or contract.get("confidence_interval") != "PERCENTILE_95"
        or contract.get("same_cluster_draws_for_all_arms") is not True
    ):
        _fail("protocol bootstrap contract drifted")
    novice = np.asarray(sorted(seed for seed, label in labels.items() if label == "NOVICE"))
    expert = np.asarray(sorted(seed for seed, label in labels.items() if label == "EXPERT"))
    numeric = {int(seed): 0 for seed in novice} | {int(seed): 1 for seed in expert}
    included = [int(seed) for seed in novice] + [int(seed) for seed in expert]
    point = {arm: _metric_pair(included, numeric, predictions[arm]) for arm in _PILOT_ARMS}
    auc = {arm: np.empty(_BOOTSTRAP_REPLICATES) for arm in _PILOT_ARMS}
    brier = {arm: np.empty(_BOOTSTRAP_REPLICATES) for arm in _PILOT_ARMS}
    generator = np.random.default_rng(random_seed)
    for replicate in range(_BOOTSTRAP_REPLICATES):
        sampled = np.concatenate(
            (generator.choice(novice, size=8, replace=True), generator.choice(expert, size=8, replace=True))
        ).tolist()
        for arm in _PILOT_ARMS:
            auc[arm][replicate], brier[arm][replicate] = _metric_pair(sampled, numeric, predictions[arm])
    metrics = {
        arm: {
            "auroc": float(point[arm][0]),
            "auroc_ci95": _interval(auc[arm]),
            "brier": float(point[arm][1]),
            "brier_ci95": _interval(brier[arm]),
        }
        for arm in _PILOT_ARMS
    }
    comparisons = {}
    for control in (_RAW_ARM, _ROTATED_ARM):
        comparisons[control] = {
            "strategic_minus_control_auroc": float(point[_STRATEGIC_ARM][0] - point[control][0]),
            "strategic_minus_control_auroc_ci95": _interval(auc[_STRATEGIC_ARM] - auc[control]),
            "strategic_minus_control_brier": float(point[_STRATEGIC_ARM][1] - point[control][1]),
            "strategic_minus_control_brier_ci95": _interval(brier[_STRATEGIC_ARM] - brier[control]),
        }
    return metrics, comparisons, random_seed


def evaluate_decision_point_pilot_v2(
    protocol: Mapping[str, Any], worker_documents: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    """Validate the two workers and run the frozen grouped feasibility analysis."""

    try:
        frozen = validate_decision_point_protocol_v2(protocol)
    except DecisionPointSignatureProtocolV2Error as error:
        raise DecisionPointSignatureEvaluatorV2Error(str(error)) from error
    if tuple(frozen.get("arms", ())) != _PILOT_ARMS:
        _fail("protocol decision-prefix arms drifted")
    if frozen.get("feature_matrix_keys") != _FEATURE_KEY_BY_ARM:
        _fail("protocol feature-matrix key mapping drifted")
    if frozen.get("feature_dimensions") != {
        _RAW_ARM: RAW_PREFIX_DIMENSION_V2,
        _ROTATED_ARM: AUGMENTED_PREFIX_DIMENSION_V2,
        _STRATEGIC_ARM: AUGMENTED_PREFIX_DIMENSION_V2,
    }:
        _fail("protocol decision-prefix dimensions drifted")
    modeling = frozen["modeling_contract"]
    if (
        modeling.get("cross_validation") != "LEAVE_ONE_POLICY_OUT_GROUPED"
        or modeling.get("standardization") != "TRAINING_FOLD_ONLY_Z_STANDARDIZATION"
        or modeling.get("classifier") != "L2_LOGISTIC_REGRESSION"
        or modeling.get("optimizer") != "SCIPY_OPTIMIZE_L_BFGS_B"
        or modeling.get("l2_strength") != _L2_STRENGTH
        or modeling.get("intercept_penalized") is not False
        or modeling.get("training_label_weighting") != "EQUAL_TOTAL_WEIGHT_PER_LABEL_WITHIN_FOLD"
        or modeling.get("heldout_policy_rows_never_enter_fit_or_standardization") is not True
    ):
        _fail("protocol modeling contract drifted")
    labels = _protocol_labels(frozen)
    matrices = _validated_policy_evidence(frozen, worker_documents)
    predictions = _grouped_predictions(labels, matrices)
    metrics, comparisons, bootstrap_seed = _bootstrap(frozen, labels, predictions)
    components = {
        "strategic_auroc_at_least_0_80": metrics[_STRATEGIC_ARM]["auroc"] >= 0.80,
        "strategic_auroc_ci95_lower_at_least_0_75": metrics[_STRATEGIC_ARM]["auroc_ci95"]["lower"] >= 0.75,
        "strategic_auroc_delta_ci95_lower_positive_vs_raw": comparisons[_RAW_ARM]["strategic_minus_control_auroc_ci95"]["lower"] > 0,
        "strategic_auroc_delta_ci95_lower_positive_vs_rotated": comparisons[_ROTATED_ARM]["strategic_minus_control_auroc_ci95"]["lower"] > 0,
        "strategic_brier_delta_ci95_upper_nonpositive_vs_raw": comparisons[_RAW_ARM]["strategic_minus_control_brier_ci95"]["upper"] <= 0,
        "strategic_brier_delta_ci95_upper_nonpositive_vs_rotated": comparisons[_ROTATED_ARM]["strategic_minus_control_brier_ci95"]["upper"] <= 0,
    }
    signal = "PASS" if all(components.values()) else "FAIL"
    included = sorted(seed for seed, label in labels.items() if label != "EXCLUDED_MIDDLE")
    return {
        "schema": PILOT_EVALUATION_SCHEMA_V2,
        "protocol_id": frozen["protocol_id"],
        "source_commit": frozen["source_commit"],
        "pilot_execution_identity": frozen["pilot_execution_identity"],
        "policy_seed_is_statistical_cluster": True,
        "policy_labels": list(frozen["policy_labels"]),
        "leave_one_policy_out_predictions": [
            {
                "seed": seed,
                "label": labels[seed],
                "state_indices": list(range(DECISION_STATE_COUNT_V2)),
                "probabilities": {
                    arm: [float(value) for value in predictions[arm][seed]]
                    for arm in _PILOT_ARMS
                },
            }
            for seed in included
        ],
        "metrics": metrics,
        "paired_strategic_comparisons": comparisons,
        "bootstrap": {
            "kind": "PAIRED_STRATIFIED_POLICY_CLUSTER_BOOTSTRAP",
            "replicates": _BOOTSTRAP_REPLICATES,
            "random_seed": bootstrap_seed,
            "confidence_interval": "PERCENTILE_95",
        },
        "provisional_design_signal_components": components,
        "provisional_design_signal": signal,
        "PROVISIONAL_DESIGN_SIGNAL_GATE": signal,
        "scientific_success": False,
        "scientific_success_claimed": False,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "SCALAR_CALIBRATION_GATE": "NOT_RUN",
        "BREAK_EVEN_GATE": "NOT_RUN",
        "OFFICIAL_EXECUTION_GATE": "NOT_RUN",
        "official_execution_allowed": False,
    }


__all__ = (
    "COLLECTOR_EVIDENCE_SCHEMA_V2",
    "DecisionPointSignatureEvaluatorV2Error",
    "PILOT_EVALUATION_SCHEMA_V2",
    "WORKER_EVIDENCE_SCHEMA_V2",
    "brier_score_v2",
    "evaluate_decision_point_pilot_v2",
    "tie_safe_auroc_v2",
)
