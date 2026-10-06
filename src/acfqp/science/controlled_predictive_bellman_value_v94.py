"""Fixed-round H2 Bellman regression, warm-started from terminal supervision."""
from collections import Counter
from copy import deepcopy
from time import perf_counter

import numpy as np

from acfqp.science.controlled_predictive_continuation_value_v91 import compose
from acfqp.science.controlled_predictive_joint_fragments_v84 import (
    FEATURE_NAMES, JointSelector, OPTIONS, QUERIES, _array, _merge, _predict,
)


TREE_PARAMETERS = dict(max_depth=8, min_samples_leaf=16, random_state=9101)
FAMILIES = ("MC_TAIL", "FQE")


class BellmanValue:
    """Shared R/F/S value for a fixed query-conditioned H2 continuation."""

    def __init__(self, trees, checkpoint, excluded_fold, training_episodes, training_method, iterations):
        self.trees, self.checkpoint, self.excluded_fold = trees, checkpoint, excluded_fold
        self.training_episodes = training_episodes
        self.training_method, self.iterations = training_method, iterations

    def predict(self, board, query, work=None):
        counts = Counter(continuation_predictions=1)
        result = _predict(self.trees[query], _array([dict(board=board)], counts), counts)[0].tolist()
        _merge(work, counts)
        return result

    def to_payload(self):
        return dict(schema="acfqp.bellman_value.v94", checkpoint=self.checkpoint,
            excluded_fold=self.excluded_fold, training_episodes=deepcopy(self.training_episodes),
            training_method=self.training_method, iterations=self.iterations,
            queries=deepcopy(QUERIES), feature_names=list(FEATURE_NAMES),
            target_components=["reward", "failure", "success"],
            tree_parameters=dict(TREE_PARAMETERS), gamma=1.0, trees=deepcopy(self.trees))

    @classmethod
    def from_payload(cls, payload):
        return cls(deepcopy(payload["trees"]), payload["checkpoint"], payload["excluded_fold"],
            deepcopy(payload["training_episodes"]), payload["training_method"], payload["iterations"])


def _fit_tree(x, y, weights, counts, family):
    from sklearn.tree import DecisionTreeRegressor

    tree = DecisionTreeRegressor(**TREE_PARAMETERS).fit(x, y, sample_weight=weights).tree_
    counts.update(tree_fits=1, fit_rows=len(x), fit_output_vectors=len(x))
    counts["mc_tail_tree_fits" if family == "MC_TAIL" else "fqe_tree_fits"] += 1
    return dict(left=tree.children_left.tolist(), right=tree.children_right.tolist(),
        feature=tree.feature.tolist(), threshold=tree.threshold.tolist(),
        values=tree.value[:, :, 0].tolist(), samples=tree.n_node_samples.tolist(),
        weighted_samples=tree.weighted_n_node_samples.tolist())


def _fit_diagnostics(tree, cache, target, counts):
    prediction = _predict(tree, cache["x"], counts)
    weights = cache["weights"]
    return dict(mean_prediction_rfs=np.average(prediction, axis=0, weights=weights).tolist(),
        mean_failure_plus_success=float(np.average(prediction[:, 1] + prediction[:, 2], weights=weights)),
        mean_target_rfs=np.average(target, axis=0, weights=weights).tolist(),
        fit_target_mse_rfs=np.average((prediction - target) ** 2, axis=0, weights=weights).tolist())


def fit_models(rows, checkpoint, iterations=128):
    """Use disjoint episode folds and a fixed number of synchronous Bellman rounds.

    Each round regresses observed n-step consequences plus the previous model's
    active-boundary value. Terminal rows never bootstrap. The initial MC trees
    remain separate immutable models; no extra fit is charged for copying them.
    """
    if iterations <= 0:
        raise ValueError("iterations must be positive")
    started = perf_counter()
    records = list(rows)
    models, folds, all_counts = {family: {} for family in FAMILIES}, {}, Counter()
    for name, excluded in (("full", None), ("fold_0", 0), ("fold_1", 1)):
        fold_start = perf_counter()
        cache_start = perf_counter()
        cache_counts = Counter(bellman_metadata_rows_read=len(records))
        selected = [row for row in records if row["episode"] < checkpoint and row["episode"] % 5 != 4
                    and (excluded is None or row["episode"] % 2 != excluded)]
        caches, episodes, query_logs = {}, {}, {}
        for query in QUERIES:
            training = [row for row in selected if row["query"] == query]
            if not training:
                raise ValueError(f"no Bellman rows for {query}, checkpoint {checkpoint}, fold {excluded}")
            active = np.asarray([row["next_active"] for row in training], dtype=bool)
            caches[query] = dict(x=_array(training, cache_counts),
                next_x=_array([dict(board=row["next_board"]) for row in training if row["next_active"]], cache_counts),
                active=active, direct=np.asarray([row["n_target"] for row in training], dtype=float),
                complete=np.asarray([row["target"] for row in training], dtype=float),
                weights=np.asarray([row["weight"] for row in training], dtype=float))
            episodes[query] = sorted({row["episode"] for row in training})
            cache_counts.update(feature_cache_builds=1, cached_training_rows=len(training),
                                cached_bootstrap_rows=int(active.sum()))
            query_logs[query] = dict(training_episodes=episodes[query], training_rows=len(training),
                training_episode_count=len(episodes[query]), bootstrap_rows=int(active.sum()),
                terminal_anchor_rows=int((~active).sum()))
        cache_seconds = perf_counter() - cache_start
        initial, mc_counts, mc_queries = {}, Counter(), {}
        mc_start = perf_counter()
        for query, cache in caches.items():
            tick, counts = perf_counter(), Counter()
            initial[query] = _fit_tree(cache["x"], cache["complete"], cache["weights"], counts, "MC_TAIL")
            diagnostics = _fit_diagnostics(initial[query], cache, cache["complete"], counts)
            mc_queries[query] = dict(counts=dict(counts), seconds=perf_counter() - tick, **diagnostics)
            mc_counts.update(counts)
        mc_seconds = perf_counter() - mc_start
        models["MC_TAIL"][name] = BellmanValue(deepcopy(initial), checkpoint, excluded,
                                               deepcopy(episodes), "MC_TAIL", 0)
        previous = deepcopy(initial)
        fqe_start = perf_counter()
        iteration_logs, fqe_counts = [], Counter()
        fqe_queries = {query: dict(counts=Counter(), seconds=0.0) for query in QUERIES}
        for iteration in range(1, iterations + 1):
            updated, diagnostics_by_query = {}, {}
            for query, cache in caches.items():
                tick, counts = perf_counter(), Counter()
                target = cache["direct"].copy()
                if cache["active"].any():
                    target[cache["active"]] += _predict(previous[query], cache["next_x"], counts)
                    counts["bootstrap_prediction_rows"] += int(cache["active"].sum())
                updated[query] = _fit_tree(cache["x"], target, cache["weights"], counts, "FQE")
                diagnostics = _fit_diagnostics(updated[query], cache, target, counts)
                elapsed = perf_counter() - tick
                diagnostics_by_query[query] = dict(counts=dict(counts), seconds=elapsed, **diagnostics)
                fqe_counts.update(counts)
                fqe_queries[query]["counts"].update(counts)
                fqe_queries[query]["seconds"] += elapsed
            previous = updated
            iteration_logs.append(dict(iteration=iteration, queries=diagnostics_by_query))
        models["FQE"][name] = BellmanValue(previous, checkpoint, excluded, deepcopy(episodes), "FQE", iterations)
        for value in fqe_queries.values():
            value["counts"] = dict(value["counts"])
        folds[name] = dict(excluded_fold=excluded, training_episodes=episodes, queries=query_logs,
            cache_counts=dict(cache_counts), cache_seconds=cache_seconds,
            MC_TAIL=dict(counts=dict(mc_counts), queries=mc_queries, seconds=mc_seconds),
            FQE=dict(counts=dict(fqe_counts), queries=fqe_queries, iterations=iteration_logs,
                     initialization="MC_TAIL", seconds=perf_counter() - fqe_start),
            seconds=perf_counter() - fold_start)
        all_counts.update(cache_counts)
        all_counts.update(mc_counts)
        all_counts.update(fqe_counts)
    return models, dict(checkpoint=checkpoint, iterations=iterations, folds=folds,
                        counts=dict(all_counts), seconds=perf_counter() - started)


def fit_heads(roots, models, checkpoint):
    """Fit unchanged V84 heads from eight paired prefix completions per root."""
    started = perf_counter()
    records = list(roots)
    counts, labels, head_fits, selectors = Counter(), {}, {}, {}
    for family in FAMILIES:
        for name, excluded in (("full", None), ("fold_0", 0), ("fold_1", 1)):
            model = models[family][name]
            if model.checkpoint != checkpoint or model.excluded_fold != excluded or any(
                episode >= checkpoint or episode % 5 == 4 or (excluded is not None and episode % 2 == excluded)
                for roster in model.training_episodes.values() for episode in roster):
                raise ValueError("continuation model violates checkpoint or episode-fold isolation")
        rows = []
        for root in records:
            episode, query = root["episode"], root["query"]
            if episode >= checkpoint or root["censored"]:
                continue
            name = "full" if episode % 5 == 4 else f"fold_{episode % 2}"
            model = models[family][name]
            prefixes = {option: {prefix["replica"]: prefix for prefix in root["prefixes"][option]}
                        for option in OPTIONS}
            if any(set(values) != set(range(8)) or len(root["prefixes"][option]) != 8
                   for option, values in prefixes.items()):
                raise ValueError("head labels require the frozen eight-replica option roster")
            completed = {option: [compose(prefixes[option][replica], model, query, counts) for replica in range(8)]
                         for option in OPTIONS}
            for option in OPTIONS[1:]:
                paired = (np.asarray(completed[option]) - np.asarray(completed["H2"])).tolist()
                rows.append(dict(board=list(root["board"]), query=query, episode=episode, option=option,
                    target=np.mean(paired, axis=0).tolist(), paired_targets=paired,
                    continuation_model=name))
            counts["completed_prefix_roots"] += 1
        labels[family] = rows
        selectors[family], head_fits[family] = JointSelector.fit(rows, checkpoint)
        counts.update(head_fits[family]["counts"])
    return selectors, labels, dict(checkpoint=checkpoint, head_fits=head_fits,
        counts=dict(counts), input_roots=len(records),
        censored_roots_excluded=sum(root["episode"] < checkpoint and root["censored"] for root in records),
        future_roots_excluded=sum(root["episode"] >= checkpoint for root in records),
        oof_episode_isolation=True, seconds=perf_counter() - started)
