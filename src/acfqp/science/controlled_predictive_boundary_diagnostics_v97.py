"""Uniform heldout scoring at deployment boundaries and later H2 states."""
from collections import Counter
from time import perf_counter

import numpy as np

from acfqp.science.controlled_predictive_paired_bellman_value_v96 import (
    QUERIES, _exact_zero, _mirror, _pair_array, _prediction,
)


MODEL_NAMES = ("PAIR_MC", "PAIR_FQE", "BOUNDARY_MC", "BOUNDARY_FQE")
SCORING_WEIGHT = 1 / 32


def _summarize(prediction, target, active_mass, coefficients, selected):
    names = ("mse_rfs", "utility_mse", "bias_rfs", "utility_bias",
             "mean_prediction_rfs", "mean_target_rfs", "mean_terminal_mass_gap",
             "mean_absolute_terminal_mass_gap")
    if not selected.any():
        return dict.fromkeys(names)
    predicted, actual = prediction[selected], target[selected]
    error = predicted - actual
    utility_error = error @ coefficients
    terminal_gap = predicted[:, 1] + predicted[:, 2] - active_mass[selected]
    # Every row retains the original 1/32 scoring weight, so weighted means
    # are ordinary means. Training-position weights never enter this path.
    return dict(mse_rfs=np.mean(error ** 2, axis=0).tolist(),
        utility_mse=float(np.mean(utility_error ** 2)), bias_rfs=np.mean(error, axis=0).tolist(),
        utility_bias=float(np.mean(utility_error)), mean_prediction_rfs=np.mean(predicted, axis=0).tolist(),
        mean_target_rfs=np.mean(actual, axis=0).tolist(), mean_terminal_mass_gap=float(np.mean(terminal_gap)),
        mean_absolute_terminal_mass_gap=float(np.mean(abs(terminal_gap))))


def evaluate_boundaries(rows, models, checkpoint):
    """Score all four frozen models once/query; stratify retained predictions."""
    started = perf_counter()
    records = list(rows)
    heldout = [row for row in records if row["episode"] < checkpoint and row["episode"] % 5 == 4]
    feature_counts = Counter(boundary_metadata_rows_read=len(records))
    model_counts = {name: Counter() for name in MODEL_NAMES}
    queries = {}
    for query, definition in QUERIES.items():
        selected = [row for row in heldout if row["query"] == query]
        size = len(selected)
        masks = dict(all=np.ones(size, dtype=bool),
            boundary=np.asarray([row["step"] == 4 for row in selected], dtype=bool),
            tail=np.asarray([row["step"] > 4 for row in selected], dtype=bool))
        strata = {name: dict(rows=int(mask.sum()),
            episodes=sorted({row["episode"] for row, keep in zip(selected, mask) if keep}),
            weight_sum=int(mask.sum()) * SCORING_WEIGHT, models={}) for name, mask in masks.items()}
        target = np.asarray([row["target"] for row in selected], dtype=float).reshape(size, 3)
        active_mass = np.asarray([int(row["candidate_active"]) - int(row["reference_active"])
                                  for row in selected])
        coefficients = np.asarray([definition["reward_weight"], -definition["failure_penalty"],
                                   definition["goal_bonus"]])
        if size:
            x = _pair_array(selected, feature_counts)
            mirrored = _mirror(x)
            zero = np.asarray([_exact_zero(row) for row in selected], dtype=bool)
            feature_counts.update(feature_cache_builds=1, boundary_heldout_rows=size)
        for name in MODEL_NAMES:
            prediction = (_prediction(models[name].trees[query], x, mirrored, zero, model_counts[name])
                          if size else np.empty((0, 3)))
            for stratum, mask in masks.items():
                strata[stratum]["models"][name] = _summarize(prediction, target, active_mass, coefficients, mask)
        queries[query] = dict(rows=size, episodes=sorted({row["episode"] for row in selected}), strata=strata)
    counts = Counter(feature_counts)
    for model_work in model_counts.values():
        counts.update(model_work)
    return dict(checkpoint=checkpoint, scoring_weight=SCORING_WEIGHT, queries=queries,
        feature_counts=dict(feature_counts), model_counts={name: dict(work) for name, work in model_counts.items()},
        counts=dict(counts), seconds=perf_counter() - started)
