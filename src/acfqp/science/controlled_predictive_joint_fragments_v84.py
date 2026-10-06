"""Learn all four fragment consequences as separate outputs of one root tree.

Each sample is one observed board with twelve targets: four prescribed options,
each carrying its complete reward/failure/success vector. Leaf size counts roots.
"""
from collections import Counter, defaultdict
from copy import deepcopy
from time import perf_counter

import numpy as np

from acfqp.science.controlled_predictive_lifelong_v77 import (
    FEATURE_NAMES as BOARD_FEATURE_NAMES, features, _predict,
)
from acfqp.science.controlled_predictive_fragments_v83 import (
    OPTIONS, ONE_STEP_OPTIONS, QUERIES, _merge, _utility,
)


FEATURE_NAMES = tuple("state_" + name for name in BOARD_FEATURE_NAMES[:-1])
TARGET_COMPONENTS = ("reward", "failure", "success")
OUTPUT_NAMES = tuple(f"{option}_{component}" for option in OPTIONS[1:] for component in TARGET_COMPONENTS)
TREE_PARAMETERS = dict(max_depth=3, min_samples_leaf=2, random_state=8301)


def _pack_roots(records):
    grouped = defaultdict(dict)
    for row in records:
        if row["option"] == "H2":
            continue
        key = row["query"], row["episode"], tuple(row["board"])
        if row["option"] in grouped[key]:
            raise ValueError("a root must supply one mean vector per fragment option")
        grouped[key][row["option"]] = row["target"]
    roots = []
    for (query, episode, board), targets in sorted(grouped.items()):
        if set(targets) != set(OPTIONS[1:]):
            raise ValueError("a root must supply all four fragment consequence vectors")
        roots.append(dict(query=query, episode=episode, board=board,
            target=[component for option in OPTIONS[1:] for component in targets[option]]))
    return roots


def _array(roots, counts):
    counts["board_feature_rows"] += len(roots)
    return np.asarray([features(row["board"], 30)[:-1] for row in roots],
                      dtype=np.float32).reshape((-1, len(FEATURE_NAMES)))


def _fit(x, y, counts):
    from sklearn.tree import DecisionTreeRegressor

    tree = DecisionTreeRegressor(**TREE_PARAMETERS).fit(x, y).tree_
    counts["tree_fits"] += 1
    counts["fit_rows"] += len(x)
    counts["fit_roots"] += len(x)
    counts["fit_output_vectors"] += 4 * len(x)
    return dict(left=tree.children_left.tolist(), right=tree.children_right.tolist(),
        feature=tree.feature.tolist(), threshold=tree.threshold.tolist(),
        values=tree.value[:, :, 0].tolist(), samples=tree.n_node_samples.tolist())


class JointSelector:
    """One joint tree per query with immutable candidate-specific output slots."""

    def __init__(self, trees, checkpoint):
        self.trees, self.checkpoint = trees, checkpoint

    @classmethod
    def fit(cls, rows, checkpoint):
        started = perf_counter()
        records = list(rows)
        roots = _pack_roots(records)
        counts = Counter(metadata_rows_read=len(records), packed_roots=len(roots))
        trees, query_logs = {}, {}
        for query in QUERIES:
            selected = [root for root in roots if root["query"] == query]
            training = [root for root in selected if root["episode"] % 5 != 4]
            heldout = [root for root in selected if root["episode"] % 5 == 4]
            if not training:
                raise ValueError(f"checkpoint {checkpoint} has no training roots for {query}")
            counts["training_roots_read"] += len(training)
            x = _array(training, counts)
            y = np.asarray([root["target"] for root in training], dtype=float).reshape((-1, 12))
            tree = trees[query] = _fit(x, y, counts)
            mse = None
            if heldout:
                counts["validation_roots_read"] += len(heldout)
                vx = _array(heldout, counts)
                vy = np.asarray([root["target"] for root in heldout], dtype=float)
                error = _predict(tree, vx, counts) - vy
                mse = np.mean(error * error, axis=0).reshape((4, 3)).tolist()
            query_logs[query] = dict(training_roots=len(training), heldout_roots=len(heldout),
                training_records=4 * len(training), heldout_records=4 * len(heldout),
                nodes=len(tree["left"]), leaves=sum(left < 0 for left in tree["left"]),
                training_target_mean=np.mean(y, axis=0).reshape((4, 3)).tolist(),
                heldout_mse_components=mse)
        train_count = sum(root["episode"] % 5 != 4 for root in roots)
        heldout_count = len(roots) - train_count
        return cls(trees, checkpoint), dict(checkpoint=checkpoint, input_records=len(records),
            reference_records_excluded=sum(row["option"] == "H2" for row in records),
            input_roots=len(roots), training_roots=train_count, heldout_roots=heldout_count,
            training_records=4 * train_count, heldout_records=4 * heldout_count,
            min_samples_leaf_unit="roots", queries=query_logs, counts=dict(counts),
            seconds=perf_counter() - started)

    def select(self, board, query, allowed=None, work=None):
        allowed = OPTIONS if allowed is None else tuple(allowed)
        if "H2" not in allowed or any(option not in OPTIONS for option in allowed):
            raise ValueError("allowed options must include H2 and use the frozen option set")
        counts = Counter(selector_decisions=1)
        predictions = {"H2": dict(target=[0.0, 0.0, 0.0], value=0.0)}
        chosen, best = "H2", 0.0
        if any(option in allowed for option in OPTIONS[1:]):
            x = _array([dict(board=board)], counts)
            vectors = _predict(self.trees[query], x, counts)[0].reshape((4, 3))
            counts["joint_prediction_roots"] += 1
            counts["predicted_output_vectors"] += 4
            for option, vector in zip(OPTIONS[1:], vectors):
                if option not in allowed:
                    continue
                target = vector.tolist()
                value = float(_utility(target, QUERIES[query]))
                predictions[option] = dict(target=target, value=value)
                counts["fragment_prediction_rows"] += 1
                if value > best:
                    chosen, best = option, value
        _merge(work, counts)
        return dict(option=chosen, predicted_advantage=predictions[chosen]["target"],
                    value=best, predictions=predictions)

    def to_payload(self):
        return dict(schema="acfqp.joint_terminal_fragments.v84", checkpoint=self.checkpoint,
            options=list(OPTIONS), queries=deepcopy(QUERIES), feature_names=list(FEATURE_NAMES),
            output_names=list(OUTPUT_NAMES), tree_parameters=dict(TREE_PARAMETERS),
            min_samples_leaf_unit="roots", trees=deepcopy(self.trees))

    @classmethod
    def from_payload(cls, payload):
        return cls(deepcopy(payload["trees"]), payload["checkpoint"])
