"""Paired Bellman updates retain fixed full-return supervision at every round."""
from collections import Counter
from copy import deepcopy
from time import perf_counter

import numpy as np

from acfqp.science.controlled_predictive_paired_bellman_value_v96 import (
    PairedBellmanValue, QUERIES, _cache, _diagnostics, _exact_zero,
    _fit_tree, _mirror, _pair_array, _prediction,
)


ANCHOR_WEIGHT = .5


def fit_models(rows, checkpoint, iterations=128):
    """Fit one paired MC initializer and fixed terminal-anchored updates.

    Source episodes, cached features, tree parameters and deployed projection
    use V96 semantics. The retained full return enters every new target with
    coefficient one half, including updates whose next pair is absorbed.
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
            raise ValueError(f"no paired anchor rows for {query}, checkpoint {checkpoint}")
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
    anchor_start = perf_counter()
    anchor_counts, iteration_logs = Counter(), []
    anchor_queries = {query: dict(counts=Counter(), seconds=0.) for query in QUERIES}
    for iteration in range(1, iterations + 1):
        updated, queries = {}, {}
        for query, cache in caches.items():
            tick, counts = perf_counter(), Counter()
            bootstrap = _prediction(previous[query], cache["next_x"], cache["next_mirrored"], cache["next_zero"], counts)
            counts.update(bootstrap_pair_rows=len(bootstrap),
                          bootstrap_nonzero_pair_rows=int((~cache["next_zero"]).sum()))
            bellman_target = cache["direct"] + bootstrap
            target = ANCHOR_WEIGHT * cache["complete"] + (1 - ANCHOR_WEIGHT) * bellman_target
            updated[query] = _fit_tree(cache, target, counts, "ANCHORED_FQE")
            counts["anchored_fqe_tree_fits"] += 1
            diagnostics = _diagnostics(updated[query], cache, target, counts, query)
            diagnostics.update(mean_bellman_target_rfs=np.average(bellman_target, axis=0,
                weights=cache["weights"]).tolist(), mean_complete_target_rfs=np.average(cache["complete"],
                axis=0, weights=cache["weights"]).tolist())
            elapsed = perf_counter() - tick
            queries[query] = dict(counts=dict(counts), seconds=elapsed, **diagnostics)
            anchor_counts.update(counts)
            anchor_queries[query]["counts"].update(counts)
            anchor_queries[query]["seconds"] += elapsed
        previous = updated
        iteration_logs.append(dict(iteration=iteration, queries=queries))
    models["ANCHORED_FQE"] = PairedBellmanValue(previous, checkpoint, deepcopy(episodes), "ANCHORED_FQE", iterations)
    anchor_seconds = perf_counter() - anchor_start
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
    for value in anchor_queries.values():
        value["counts"] = dict(value["counts"])
    counts = Counter(cache_counts)
    counts.update(mc_counts)
    counts.update(anchor_counts)
    counts.update(heldout_counts)
    return models, dict(checkpoint=checkpoint, iterations=iterations, anchor_weight=ANCHOR_WEIGHT,
        training_episodes=episodes, queries=query_logs, cache_counts=dict(cache_counts), cache_seconds=cache_seconds,
        PAIR_MC=dict(counts=dict(mc_counts), queries=mc_queries, seconds=mc_seconds),
        ANCHORED_FQE=dict(counts=dict(anchor_counts), queries=anchor_queries, iterations=iteration_logs,
            initialization="PAIR_MC", anchor_weight=ANCHOR_WEIGHT, seconds=anchor_seconds),
        heldout=dict(counts=dict(heldout_counts), queries=heldout_queries, seconds=perf_counter() - heldout_start),
        counts=dict(counts), seconds=perf_counter() - started)
