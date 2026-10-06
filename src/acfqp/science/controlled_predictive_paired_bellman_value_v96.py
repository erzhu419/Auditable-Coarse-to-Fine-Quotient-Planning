"""Paired H2 Bellman regression with the deployed antisymmetric operator."""
from collections import Counter
from copy import deepcopy
from time import perf_counter

import numpy as np

from acfqp.science.controlled_predictive_paired_continuation_value_v92 import (
    FEATURE_NAMES, TREE_PARAMETERS, QUERIES, _pair_array, _mirror, _predict, _merge,
)


def _exact_zero(row):
    cactive, ractive = row["candidate_active"], row["reference_active"]
    return ((not cactive and not ractive)
            or (cactive == ractive and tuple(row["candidate_board"]) == tuple(row["reference_board"])))


def _prediction(tree, x, mirrored, zero_mask, counts):
    """One inference rule for bootstrap, diagnostics, and deployed predictions."""
    n = len(zero_mask)
    counts["paired_continuation_predictions"] += n
    counts["paired_exact_zero_predictions"] += int(zero_mask.sum())
    result = np.zeros((n, 3), dtype=float)
    active = np.flatnonzero(~zero_mask)
    if len(active):
        predictions = _predict(tree, np.concatenate((x[active], mirrored[active])), counts)
        result[active] = (predictions[:len(active)] - predictions[len(active):]) * .5
    return result


class PairedBellmanValue:
    def __init__(self, trees, checkpoint, training_episodes, family, iterations):
        self.trees, self.checkpoint = trees, checkpoint
        self.training_episodes, self.family, self.iterations = training_episodes, family, iterations

    def predict_pair(self, cboard, rboard, cactive, ractive, query, work=None):
        counts = Counter()
        row = dict(candidate_board=cboard, reference_board=rboard,
                   candidate_active=cactive, reference_active=ractive)
        zero = np.asarray([_exact_zero(row)], dtype=bool)
        x = np.zeros((1, len(FEATURE_NAMES)), dtype=np.float32) if zero[0] else _pair_array([row], counts)
        result = _prediction(self.trees[query], x, _mirror(x), zero, counts)[0].tolist()
        _merge(work, counts)
        return result

    def to_payload(self):
        return dict(schema="acfqp.paired_bellman_value.v96", checkpoint=self.checkpoint,
            training_episodes=deepcopy(self.training_episodes), family=self.family, iterations=self.iterations,
            queries=deepcopy(QUERIES), feature_names=list(FEATURE_NAMES),
            target_components=["reward", "failure", "success"], tree_parameters=dict(TREE_PARAMETERS),
            gamma=1.0, mirrored_half_weights=True, antisymmetric_prediction=True, trees=deepcopy(self.trees))

    @classmethod
    def from_payload(cls, payload):
        return cls(deepcopy(payload["trees"]), payload["checkpoint"],
                   deepcopy(payload["training_episodes"]), payload["family"], payload["iterations"])


def _fit_tree(cache, target, counts, family):
    from sklearn.tree import DecisionTreeRegressor

    y = np.concatenate((target, -target))
    tree = DecisionTreeRegressor(**TREE_PARAMETERS).fit(cache["fit_x"], y,
                                                        sample_weight=cache["fit_weights"]).tree_
    counts.update(tree_fits=1, fit_rows=len(y), fit_output_vectors=len(y))
    counts["pair_mc_tree_fits" if family == "PAIR_MC" else "pair_fqe_tree_fits"] += 1
    return dict(left=tree.children_left.tolist(), right=tree.children_right.tolist(),
        feature=tree.feature.tolist(), threshold=tree.threshold.tolist(), values=tree.value[:, :, 0].tolist(),
        samples=tree.n_node_samples.tolist(), weighted_samples=tree.weighted_n_node_samples.tolist())


def _cache(rows, counts):
    x = _pair_array(rows, counts)
    mirrored = _mirror(x)
    zero = np.asarray([_exact_zero(row) for row in rows], dtype=bool)
    next_rows = [dict(candidate_board=row["next_candidate_board"],
        reference_board=row["next_reference_board"], candidate_active=row["next_candidate_active"],
        reference_active=row["next_reference_active"]) for row in rows]
    next_zero = np.asarray([_exact_zero(row) for row in next_rows], dtype=bool)
    next_x = np.zeros_like(x)
    if (~next_zero).any():
        next_x[~next_zero] = _pair_array([row for row, skip in zip(next_rows, next_zero) if not skip], counts)
    weights = np.asarray([row["weight"] for row in rows], dtype=float)
    counts.update(feature_cache_builds=1, cached_current_pair_rows=len(rows),
                  cached_nonzero_next_pair_rows=int((~next_zero).sum()))
    return dict(x=x, mirrored=mirrored, zero=zero, next_x=next_x, next_mirrored=_mirror(next_x),
        next_zero=next_zero, fit_x=np.concatenate((x, mirrored)),
        fit_weights=np.concatenate((weights * .5, weights * .5)), weights=weights,
        direct=np.asarray([row["n_target"] for row in rows], dtype=float),
        complete=np.asarray([row["target"] for row in rows], dtype=float),
        active_mass=np.asarray([int(row["candidate_active"]) - int(row["reference_active"]) for row in rows]))


def _diagnostics(tree, cache, target, counts, query=None):
    prediction = _prediction(tree, cache["x"], cache["mirrored"], cache["zero"], counts)
    terminal_gap = prediction[:, 1] + prediction[:, 2] - cache["active_mass"]
    result = dict(mean_prediction_rfs=np.average(prediction, axis=0, weights=cache["weights"]).tolist(),
        mean_target_rfs=np.average(target, axis=0, weights=cache["weights"]).tolist(),
        fit_target_mse_rfs=np.average((prediction - target) ** 2, axis=0, weights=cache["weights"]).tolist(),
        mean_terminal_mass_gap=float(np.average(terminal_gap, weights=cache["weights"])),
        mean_absolute_terminal_mass_gap=float(np.average(abs(terminal_gap), weights=cache["weights"])))
    if query is not None:
        definition = QUERIES[query]
        coefficients = np.asarray([definition["reward_weight"], -definition["failure_penalty"],
                                   definition["goal_bonus"]])
        result["utility_mse"] = float(np.average(((prediction - target) @ coefficients) ** 2,
                                                weights=cache["weights"]))
    return result


def fit_models(rows, checkpoint, iterations=128):
    """Fit full-history paired MC and exactly the prescribed Bellman updates.

    New deployment roots do not generate training labels, so no extra folds or
    selector heads are fitted. Heldout episodes and future source batches are
    excluded from the initial model and every subsequent Bellman target.
    """
    if iterations <= 0:
        raise ValueError("iterations must be positive")
    started = perf_counter()
    records = list(rows)
    selected = [row for row in records if row["episode"] < checkpoint and row["episode"] % 5 != 4]
    cache_start = perf_counter()
    cache_counts = Counter(paired_metadata_rows_read=len(records), paired_training_rows_read=len(selected))
    caches, episodes, query_logs = {}, {}, {}
    for query in QUERIES:
        training = [row for row in selected if row["query"] == query]
        if not training:
            raise ValueError(f"no paired Bellman rows for {query}, checkpoint {checkpoint}")
        cache = caches[query] = _cache(training, cache_counts)
        episodes[query] = sorted({row["episode"] for row in training})
        query_logs[query] = dict(training_episodes=episodes[query], training_episode_count=len(episodes[query]),
            training_rows=len(training), mirrored_training_rows=2 * len(training),
            weight_sum=float(cache["weights"].sum()), current_exact_zero_rows=int(cache["zero"].sum()),
            next_exact_zero_rows=int(cache["next_zero"].sum()),
            next_both_absorbed_rows=sum(not row["next_candidate_active"] and not row["next_reference_active"]
                                        for row in training))
    cache_seconds = perf_counter() - cache_start
    mc_start = perf_counter()
    initial, mc_counts, mc_queries = {}, Counter(), {}
    for query, cache in caches.items():
        tick, counts = perf_counter(), Counter()
        initial[query] = _fit_tree(cache, cache["complete"], counts, "PAIR_MC")
        diagnostics = _diagnostics(initial[query], cache, cache["complete"], counts, query)
        mc_queries[query] = dict(counts=dict(counts), seconds=perf_counter() - tick, **diagnostics)
        mc_counts.update(counts)
    mc_seconds = perf_counter() - mc_start
    models = {"PAIR_MC": PairedBellmanValue(deepcopy(initial), checkpoint, deepcopy(episodes), "PAIR_MC", 0)}
    previous = deepcopy(initial)
    fqe_start = perf_counter()
    fqe_counts, iteration_logs = Counter(), []
    fqe_queries = {query: dict(counts=Counter(), seconds=0.) for query in QUERIES}
    for iteration in range(1, iterations + 1):
        updated, queries = {}, {}
        for query, cache in caches.items():
            tick, counts = perf_counter(), Counter()
            bootstrap = _prediction(previous[query], cache["next_x"], cache["next_mirrored"], cache["next_zero"], counts)
            counts.update(bootstrap_pair_rows=len(bootstrap),
                          bootstrap_nonzero_pair_rows=int((~cache["next_zero"]).sum()))
            target = cache["direct"] + bootstrap
            updated[query] = _fit_tree(cache, target, counts, "PAIR_FQE")
            diagnostics = _diagnostics(updated[query], cache, target, counts, query)
            elapsed = perf_counter() - tick
            queries[query] = dict(counts=dict(counts), seconds=elapsed, **diagnostics)
            fqe_counts.update(counts)
            fqe_queries[query]["counts"].update(counts)
            fqe_queries[query]["seconds"] += elapsed
        previous = updated
        iteration_logs.append(dict(iteration=iteration, queries=queries))
    models["PAIR_FQE"] = PairedBellmanValue(previous, checkpoint, deepcopy(episodes), "PAIR_FQE", iterations)
    fqe_seconds = perf_counter() - fqe_start
    heldout_start, heldout_counts, heldout_queries = perf_counter(), Counter(), {}
    for query in QUERIES:
        heldout = [row for row in records if row["query"] == query
                   and row["episode"] < checkpoint and row["episode"] % 5 == 4]
        if not heldout:
            continue
        x = _pair_array(heldout, heldout_counts)
        cache = dict(x=x, mirrored=_mirror(x),
            zero=np.asarray([_exact_zero(row) for row in heldout], dtype=bool),
            weights=np.asarray([row["weight"] for row in heldout], dtype=float),
            active_mass=np.asarray([int(row["candidate_active"]) - int(row["reference_active"]) for row in heldout]))
        target = np.asarray([row["target"] for row in heldout], dtype=float)
        heldout_counts.update(heldout_pair_rows=len(heldout), feature_cache_builds=1)
        heldout_queries[query] = dict(episodes=sorted({row["episode"] for row in heldout}), rows=len(heldout),
            weight_sum=float(cache["weights"].sum()), **{
                family: _diagnostics(model.trees[query], cache, target, heldout_counts, query)
                for family, model in models.items()})
    for value in fqe_queries.values():
        value["counts"] = dict(value["counts"])
    counts = Counter(cache_counts)
    counts.update(mc_counts)
    counts.update(fqe_counts)
    counts.update(heldout_counts)
    return models, dict(checkpoint=checkpoint, iterations=iterations, training_episodes=episodes,
        queries=query_logs, cache_counts=dict(cache_counts), cache_seconds=cache_seconds,
        PAIR_MC=dict(counts=dict(mc_counts), queries=mc_queries, seconds=mc_seconds),
        PAIR_FQE=dict(counts=dict(fqe_counts), queries=fqe_queries, iterations=iteration_logs,
                      initialization="PAIR_MC", seconds=fqe_seconds),
        heldout=dict(counts=dict(heldout_counts), queries=heldout_queries,
                     seconds=perf_counter() - heldout_start),
        counts=dict(counts), seconds=perf_counter() - started)
