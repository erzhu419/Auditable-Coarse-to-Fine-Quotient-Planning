"""Episode-disjoint, antisymmetric H2 continuation-difference learning."""
from collections import Counter
from copy import deepcopy
from time import perf_counter

import numpy as np

from acfqp.science.controlled_predictive_joint_fragments_v84 import (
    FEATURE_NAMES as BOARD_FEATURE_NAMES, QUERIES, _array, _merge, _predict,
)


TREE_PARAMETERS = dict(max_depth=8, min_samples_leaf=16, random_state=9201)
FEATURE_NAMES = tuple("mean_" + name for name in BOARD_FEATURE_NAMES) + tuple(
    "difference_" + name for name in BOARD_FEATURE_NAMES) + ("candidate_active", "reference_active")


def _pair_array(rows, counts):
    left = _array([dict(board=row["candidate_board"]) for row in rows], counts)
    right = _array([dict(board=row["reference_board"]) for row in rows], counts)
    active = np.asarray([[row["candidate_active"], row["reference_active"]] for row in rows], dtype=np.float32)
    counts["paired_feature_rows"] += len(rows)
    return np.concatenate(((left + right) * .5, left - right, active), axis=1)


def _mirror(x):
    reversed_x = x.copy()
    reversed_x[:, 36:72] *= -1
    reversed_x[:, 72:74] = x[:, [73, 72]]
    return reversed_x


class PairedContinuation:
    """A joint R/F/S difference model with exact swap and diagonal constraints."""

    def __init__(self, trees, checkpoint, excluded_fold=None, training_episodes=None):
        self.trees, self.checkpoint, self.excluded_fold = trees, checkpoint, excluded_fold
        self.training_episodes = training_episodes or {}

    @classmethod
    def fit(cls, rows, checkpoint, excluded_fold=None):
        started = perf_counter()
        from sklearn.tree import DecisionTreeRegressor

        if excluded_fold not in (None, 0, 1):
            raise ValueError("excluded_fold must be None, 0 or 1")
        records = list(rows)
        training = [row for row in records if row["episode"] < checkpoint and row["episode"] % 5 != 4
                    and (excluded_fold is None or row["episode"] % 2 != excluded_fold)]
        counts = Counter(paired_metadata_rows_read=len(records), paired_training_rows_read=len(training))
        trees, episodes, queries = {}, {}, {}
        for query in QUERIES:
            tick = perf_counter()
            selected = [row for row in training if row["query"] == query]
            if not selected:
                raise ValueError(f"no paired H2 rows for {query}, checkpoint {checkpoint}, fold {excluded_fold}")
            original_x = _pair_array(selected, counts)
            original_y = np.asarray([row["target"] for row in selected], dtype=float)
            original_weight = np.asarray([row["weight"] for row in selected], dtype=float)
            x = np.concatenate((original_x, _mirror(original_x)))
            y = np.concatenate((original_y, -original_y))
            weights = np.concatenate((original_weight * .5, original_weight * .5))
            tree = DecisionTreeRegressor(**TREE_PARAMETERS).fit(x, y, sample_weight=weights).tree_
            trees[query] = dict(left=tree.children_left.tolist(), right=tree.children_right.tolist(),
                feature=tree.feature.tolist(), threshold=tree.threshold.tolist(), values=tree.value[:, :, 0].tolist(),
                samples=tree.n_node_samples.tolist(), weighted_samples=tree.weighted_n_node_samples.tolist())
            counts.update(tree_fits=1, paired_continuation_tree_fits=1, fit_rows=len(x),
                          fit_output_vectors=len(x), mirrored_training_rows=len(x))
            episodes[query] = sorted({row["episode"] for row in selected})
            queries[query] = dict(training_rows=len(selected), mirrored_training_rows=len(x),
                training_episodes=episodes[query], training_episode_count=len(episodes[query]),
                weight_sum=float(weights.sum()), nodes=tree.node_count,
                leaves=int(sum(tree.children_left < 0)), seconds=perf_counter() - tick)
        return cls(trees, checkpoint, excluded_fold, episodes), dict(checkpoint=checkpoint,
            excluded_fold=excluded_fold, input_rows=len(records), training_rows=len(training),
            queries=queries, counts=dict(counts), seconds=perf_counter() - started)

    def predict_pair(self, cboard, rboard, cactive, ractive, query, work=None):
        counts = Counter(paired_continuation_predictions=1)
        if (not cactive and not ractive) or (cactive == ractive and tuple(cboard) == tuple(rboard)):
            counts["paired_exact_zero_predictions"] += 1
            _merge(work, counts)
            return [0., 0., 0.]
        x = _pair_array([dict(candidate_board=cboard, reference_board=rboard,
                             candidate_active=cactive, reference_active=ractive)], counts)
        predictions = _predict(self.trees[query], np.concatenate((x, _mirror(x))), counts)
        result = ((predictions[0] - predictions[1]) * .5).tolist()
        _merge(work, counts)
        return result

    def to_payload(self):
        return dict(schema="acfqp.paired_continuation_value.v92", checkpoint=self.checkpoint,
            excluded_fold=self.excluded_fold, training_episodes=deepcopy(self.training_episodes),
            queries=deepcopy(QUERIES), feature_names=list(FEATURE_NAMES),
            target_components=["reward", "failure", "success"], tree_parameters=dict(TREE_PARAMETERS),
            mirrored_half_weights=True, antisymmetric_prediction=True, trees=deepcopy(self.trees))

    @classmethod
    def from_payload(cls, payload):
        return cls(deepcopy(payload["trees"]), payload["checkpoint"], payload["excluded_fold"],
                   deepcopy(payload["training_episodes"]))


def fit_models(rows, checkpoint):
    started = perf_counter()
    records = list(rows)
    models, fits, counts = {}, {}, Counter()
    for name, fold in (("full", None), ("fold_0", 0), ("fold_1", 1)):
        models[name], fits[name] = PairedContinuation.fit(records, checkpoint, fold)
        counts.update(fits[name]["counts"])
    return models, dict(fits=fits, counts=dict(counts), seconds=perf_counter() - started)
