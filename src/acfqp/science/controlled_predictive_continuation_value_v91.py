"""Shared H2 continuation consequences and episode-disjoint fragment labels."""
from collections import Counter
from copy import deepcopy
from time import perf_counter

import numpy as np

from acfqp.science.controlled_predictive_joint_fragments_v84 import (
    FEATURE_NAMES, JointSelector, OPTIONS, QUERIES, _array, _merge, _predict, _utility,
)


TREE_PARAMETERS = dict(max_depth=8, min_samples_leaf=16, random_state=9101)


class ContinuationValue:
    """One weighted three-output tree per query for a fixed H2 continuation."""

    def __init__(self, trees, checkpoint, excluded_fold=None, training_episodes=None):
        self.trees, self.checkpoint = trees, checkpoint
        self.excluded_fold = excluded_fold
        self.training_episodes = training_episodes or {}

    @classmethod
    def fit(cls, tail_rows, checkpoint, excluded_fold=None):
        started = perf_counter()
        from sklearn.tree import DecisionTreeRegressor

        if excluded_fold not in (None, 0, 1):
            raise ValueError("excluded_fold must be None, 0, or 1")
        records = list(tail_rows)
        counts = Counter(tail_metadata_rows_read=len(records))
        training = [row for row in records if row["episode"] < checkpoint
            and row["episode"] % 5 != 4
            and (excluded_fold is None or row["episode"] % 2 != excluded_fold)]
        trees, queries, episodes = {}, {}, {}
        for query in QUERIES:
            tick = perf_counter()
            selected = [row for row in training if row["query"] == query]
            if not selected:
                raise ValueError(f"no H2 tail training rows for {query}, checkpoint {checkpoint}, fold {excluded_fold}")
            counts["tail_training_rows_read"] += len(selected)
            x = _array(selected, counts)
            y = np.asarray([row["target"] for row in selected], dtype=float)
            weights = np.asarray([row["weight"] for row in selected], dtype=float)
            tree = DecisionTreeRegressor(**TREE_PARAMETERS).fit(x, y, sample_weight=weights).tree_
            counts.update(tree_fits=1, continuation_tree_fits=1,
                          fit_rows=len(x), fit_output_vectors=len(x))
            trees[query] = dict(left=tree.children_left.tolist(), right=tree.children_right.tolist(),
                feature=tree.feature.tolist(), threshold=tree.threshold.tolist(),
                values=tree.value[:, :, 0].tolist(), samples=tree.n_node_samples.tolist(),
                weighted_samples=tree.weighted_n_node_samples.tolist())
            episodes[query] = sorted({row["episode"] for row in selected})
            queries[query] = dict(training_rows=len(selected), training_episodes=episodes[query],
                training_episode_count=len(episodes[query]), weight_sum=float(weights.sum()),
                nodes=tree.node_count, leaves=int(sum(tree.children_left < 0)),
                seconds=perf_counter() - tick)
        model = cls(trees, checkpoint, excluded_fold, episodes)
        return model, dict(checkpoint=checkpoint, excluded_fold=excluded_fold,
            input_rows=len(records), training_rows=len(training), queries=queries,
            counts=dict(counts), seconds=perf_counter() - started)

    def predict(self, board, query, work=None):
        counts = Counter(continuation_predictions=1)
        value = _predict(self.trees[query], _array([dict(board=board)], counts), counts)[0].tolist()
        _merge(work, counts)
        return value

    def to_payload(self):
        return dict(schema="acfqp.continuation_value.v91", checkpoint=self.checkpoint,
            excluded_fold=self.excluded_fold, training_episodes=deepcopy(self.training_episodes),
            queries=deepcopy(QUERIES), feature_names=list(FEATURE_NAMES),
            target_components=["reward", "failure", "success"],
            tree_parameters=dict(TREE_PARAMETERS), trees=deepcopy(self.trees))

    @classmethod
    def from_payload(cls, payload):
        return cls(deepcopy(payload["trees"]), payload["checkpoint"],
                   payload["excluded_fold"], deepcopy(payload["training_episodes"]))


def compose(prefix, model, query, work=None):
    """Add a tail only at an active boundary, never after a terminal outcome."""
    direct = list(prefix["direct"])
    if prefix["status"] in ("WON", "LOST"):
        return direct
    if prefix["status"] != "ACTIVE":
        raise ValueError("a cutoff cannot supply a complete continuation label")
    tail = model.predict(prefix["boundary_board"], query, work)
    return [observed + predicted for observed, predicted in zip(direct, tail)]


def fit_decomposed(roots, tail_rows, checkpoint):
    """Cross-fit by original episode, then fit the unchanged V84 root selector.

    Both candidates and their H2 reference stop at the same four-action boundary.
    Their shared continuation model excludes the entire original episode fold.
    Heldout labels use the full model only for the selector's heldout diagnostics.
    """
    started = perf_counter()
    records, tails = list(roots), list(tail_rows)
    models, tail_fits, counts = {}, {}, Counter()
    for name, fold in (("full", None), ("fold_0", 0), ("fold_1", 1)):
        models[name], tail_fits[name] = ContinuationValue.fit(tails, checkpoint, fold)
        counts.update(tail_fits[name]["counts"])
    tick = perf_counter()
    rows, variances = [], []
    eligible = [root for root in records if root["episode"] < checkpoint and not root["censored"]]
    for root in eligible:
        query, episode = root["query"], root["episode"]
        heldout = episode % 5 == 4
        model_name = "full" if heldout else f"fold_{episode % 2}"
        model = models[model_name]
        if not heldout and any(episode in roster for roster in model.training_episodes.values()):
            raise ValueError("original episode entered its own continuation model")
        prefixes = {option: {prefix["replica"]: prefix for prefix in root["prefixes"][option]}
                    for option in OPTIONS}
        replicas = sorted(prefixes["H2"])
        if (not replicas or any(set(prefixes[option]) != set(replicas)
                or len(prefixes[option]) != len(root["prefixes"][option]) for option in OPTIONS)):
            raise ValueError("decomposition requires matching complete option replica rosters")
        completed = {option: {replica: compose(prefixes[option][replica], model, query, counts)
                             for replica in replicas} for option in OPTIONS}
        for option in OPTIONS[1:]:
            paired = [[candidate - reference for candidate, reference in
                       zip(completed[option][replica], completed["H2"][replica])]
                      for replica in replicas]
            rows.append(dict(board=list(root["board"]), query=query, episode=episode, option=option,
                target=np.mean(paired, axis=0).tolist(), paired_targets=paired,
                paired_replicas=replicas, continuation_model=model_name))
            utilities = [_utility(target, QUERIES[query]) for target in paired]
            variances.append(dict(query=query, episode=episode, option=option, heldout=heldout,
                replicas=len(replicas), paired_utility_sample_variance=(
                    float(np.var(utilities, ddof=1)) if len(replicas) > 1 else None)))
        counts.update(decomposed_roots=1, decomposed_candidate_labels=4,
                      decomposed_pair_vectors=4 * len(replicas))
    label_seconds = perf_counter() - tick
    selector, head_fit = JointSelector.fit(rows, checkpoint)
    counts.update(head_fit["counts"])
    return selector, models, rows, dict(checkpoint=checkpoint, tail_fits=tail_fits,
        head_fit=head_fit, counts=dict(counts), label_variance=variances,
        input_roots=len(records), eligible_roots=len(eligible),
        censored_roots_excluded=sum(root["episode"] < checkpoint and root["censored"] for root in records),
        future_roots_excluded=sum(root["episode"] >= checkpoint for root in records),
        oof_episode_isolation=True, label_seconds=label_seconds, seconds=perf_counter() - started)
