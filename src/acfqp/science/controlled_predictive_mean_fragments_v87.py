"""Update the shared fragment mean while preserving the source candidate order."""
from collections import Counter
from copy import deepcopy
from time import perf_counter

import numpy as np

from acfqp.science.controlled_predictive_centered_fragments_v85 import CenteredSelector
from acfqp.science.controlled_predictive_joint_fragments_v84 import (
    OPTIONS, ONE_STEP_OPTIONS, QUERIES, FEATURE_NAMES, TARGET_COMPONENTS,
    TREE_PARAMETERS, _pack_roots, _array, _predict, _merge, _utility,
)


def _fit(x, y, counts):
    from sklearn.tree import DecisionTreeRegressor

    tree = DecisionTreeRegressor(**TREE_PARAMETERS).fit(x, y).tree_
    counts["tree_fits"] += 1
    counts["mean_tree_fits"] += 1
    counts["fit_rows"] += len(x)
    counts["fit_roots"] += len(x)
    counts["fit_output_vectors"] += len(x)
    return dict(left=tree.children_left.tolist(), right=tree.children_right.tolist(),
        feature=tree.feature.tolist(), threshold=tree.threshold.tolist(),
        values=tree.value[:, :, 0].tolist(), samples=tree.n_node_samples.tolist())


class MeanSelector:
    """A learned mean changes intervention acceptance, with candidate order fixed."""

    def __init__(self, mean_trees, checkpoint, source):
        self.mean_trees, self.checkpoint, self.source = mean_trees, checkpoint, source

    @classmethod
    def fit(cls, rows, checkpoint, source):
        if checkpoint != source.checkpoint:
            raise ValueError("the source selector must match the mean fit checkpoint")
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
            y = np.asarray([root["target"] for root in training], dtype=float).reshape((-1, 4, 3)).mean(axis=1)
            tree = trees[query] = _fit(x, y, counts)
            mse = None
            if heldout:
                counts["validation_roots_read"] += len(heldout)
                vx = _array(heldout, counts)
                vy = np.asarray([root["target"] for root in heldout], dtype=float).reshape((-1, 4, 3)).mean(axis=1)
                error = _predict(tree, vx, counts) - vy
                mse = np.mean(error * error, axis=0).tolist()
            query_logs[query] = dict(training_roots=len(training), heldout_roots=len(heldout),
                training_records=4 * len(training), heldout_records=4 * len(heldout),
                nodes=len(tree["left"]), leaves=sum(left < 0 for left in tree["left"]),
                training_target_mean=y.mean(axis=0).tolist(), heldout_mse_components=mse)
        train_count = sum(root["episode"] % 5 != 4 for root in roots)
        heldout_count = len(roots) - train_count
        selector = cls(trees, checkpoint, CenteredSelector.from_payload(source.to_payload()))
        return selector, dict(checkpoint=checkpoint, source_checkpoint=source.checkpoint,
            input_records=len(records), reference_records_excluded=sum(row["option"] == "H2" for row in records),
            input_roots=len(roots), training_roots=train_count, heldout_roots=heldout_count,
            training_records=4 * train_count, heldout_records=4 * heldout_count,
            min_samples_leaf_unit="roots", source_tree_fits=0, queries=query_logs,
            counts=dict(counts), seconds=perf_counter() - started)

    def select(self, board, query, allowed=None, work=None):
        allowed = OPTIONS if allowed is None else tuple(allowed)
        if "H2" not in allowed or any(option not in OPTIONS for option in allowed):
            raise ValueError("allowed options must include H2 and use the frozen option set")
        counts = Counter(mean_selector_decisions=1)
        predictions = {"H2": dict(target=[0.0, 0.0, 0.0], value=0.0, ranking_value=0.0)}
        chosen, best = "H2", 0.0
        alternatives = [option for option in OPTIONS[1:] if option in allowed]
        if alternatives:
            source_counts = Counter()
            original = self.source.select(board, query, allowed=OPTIONS, work=source_counts)["predictions"]
            counts.update(source_counts)
            counts["source_prediction_roots"] += 1
            source_mean = np.asarray([original[option]["target"] for option in OPTIONS[1:]]).mean(axis=0)
            x = _array([dict(board=board)], counts)
            mean_counts = Counter()
            new_mean = _predict(self.mean_trees[query], x, mean_counts)[0]
            counts.update(mean_counts)
            counts.update({f"mean_{name}": value for name, value in mean_counts.items()})
            counts["mean_prediction_roots"] += 1
            counts["mean_predicted_output_vectors"] += 1
            shift = new_mean - source_mean
            for option in alternatives:
                target = (np.asarray(original[option]["target"]) + shift).tolist()
                predictions[option] = dict(target=target, value=float(_utility(target, QUERIES[query])),
                                           ranking_value=original[option]["value"])
            # Choose by the source order before testing the shifted H2 threshold.
            # Re-ranking shifted floats could introduce new numerical ties.
            candidate = max(alternatives, key=lambda option: original[option]["value"])
            if predictions[candidate]["value"] > 0:
                chosen, best = candidate, predictions[candidate]["value"]
        _merge(work, counts)
        return dict(option=chosen, predicted_advantage=predictions[chosen]["target"],
                    value=best, predictions=predictions)

    def to_payload(self):
        return dict(schema="acfqp.mean_terminal_fragments.v87", checkpoint=self.checkpoint,
            options=list(OPTIONS), queries=deepcopy(QUERIES), feature_names=list(FEATURE_NAMES),
            output_names=list(TARGET_COMPONENTS), tree_parameters=dict(TREE_PARAMETERS),
            min_samples_leaf_unit="roots", mean_trees=deepcopy(self.mean_trees), source=self.source.to_payload())

    @classmethod
    def from_payload(cls, payload):
        return cls(deepcopy(payload["mean_trees"]), payload["checkpoint"],
                   CenteredSelector.from_payload(payload["source"]))
