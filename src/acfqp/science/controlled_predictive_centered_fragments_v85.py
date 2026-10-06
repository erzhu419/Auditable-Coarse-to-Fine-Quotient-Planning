"""Learn candidate differences while retaining the frozen joint model's mean."""
from collections import Counter
from copy import deepcopy
from time import perf_counter

import numpy as np

from acfqp.science.controlled_predictive_joint_fragments_v84 import (
    JointSelector, OPTIONS, ONE_STEP_OPTIONS, QUERIES, FEATURE_NAMES, OUTPUT_NAMES,
    TREE_PARAMETERS, _pack_roots, _array, _fit, _predict, _merge, _utility,
)


def _center(vectors):
    return vectors - vectors.mean(axis=1, keepdims=True)


def _prediction(tree, x, counts, role):
    work = Counter()
    vectors = _predict(tree, x, work).reshape((-1, 4, 3))
    counts.update(work)
    counts.update({f"{role}_{name}": value for name, value in work.items()})
    counts[f"{role}_prediction_roots"] += len(x)
    counts[f"{role}_predicted_output_vectors"] += 4 * len(x)
    return vectors


def _reconstruct(anchor, residual):
    return anchor.mean(axis=1, keepdims=True) + _center(residual)


class CenteredSelector:
    """A fixed anchor's mean plus separately learned, centered candidate outputs."""

    def __init__(self, trees, checkpoint, anchor):
        self.trees, self.checkpoint, self.anchor = trees, checkpoint, anchor

    @classmethod
    def fit(cls, rows, checkpoint, anchor):
        if checkpoint != anchor.checkpoint:
            raise ValueError("the frozen anchor must match the residual fit checkpoint")
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
            y = np.asarray([root["target"] for root in training], dtype=float).reshape((-1, 4, 3))
            residual = _center(y)
            tree = trees[query] = _fit(x, residual.reshape((-1, 12)), counts)
            counts["centered_target_roots"] += len(training)
            residual_mse, reconstructed_mse = None, None
            if heldout:
                counts["validation_roots_read"] += len(heldout)
                vx = _array(heldout, counts)
                vy = np.asarray([root["target"] for root in heldout], dtype=float).reshape((-1, 4, 3))
                predicted_residual = _prediction(tree, vx, counts, "residual")
                predicted_anchor = _prediction(anchor.trees[query], vx, counts, "anchor")
                residual_mse = np.mean((_center(predicted_residual) - _center(vy)) ** 2, axis=0).tolist()
                reconstructed_mse = np.mean((_reconstruct(predicted_anchor, predicted_residual) - vy) ** 2,
                                            axis=0).tolist()
            query_logs[query] = dict(training_roots=len(training), heldout_roots=len(heldout),
                training_records=4 * len(training), heldout_records=4 * len(heldout),
                nodes=len(tree["left"]), leaves=sum(left < 0 for left in tree["left"]),
                training_target_mean=y.mean(axis=0).tolist(), training_residual_mean=residual.mean(axis=0).tolist(),
                heldout_residual_mse_components=residual_mse, heldout_mse_components=reconstructed_mse)
        train_count = sum(root["episode"] % 5 != 4 for root in roots)
        heldout_count = len(roots) - train_count
        selector = cls(trees, checkpoint, JointSelector.from_payload(anchor.to_payload()))
        return selector, dict(checkpoint=checkpoint, anchor_checkpoint=anchor.checkpoint,
            input_records=len(records), reference_records_excluded=sum(row["option"] == "H2" for row in records),
            input_roots=len(roots), training_roots=train_count, heldout_roots=heldout_count,
            training_records=4 * train_count, heldout_records=4 * heldout_count,
            min_samples_leaf_unit="roots", anchor_tree_fits=0, queries=query_logs,
            counts=dict(counts), seconds=perf_counter() - started)

    def select(self, board, query, allowed=None, work=None):
        allowed = OPTIONS if allowed is None else tuple(allowed)
        if "H2" not in allowed or any(option not in OPTIONS for option in allowed):
            raise ValueError("allowed options must include H2 and use the frozen option set")
        counts = Counter(selector_decisions=1)
        predictions = {"H2": dict(target=[0.0, 0.0, 0.0], value=0.0)}
        chosen, best = "H2", 0.0
        if any(option in allowed for option in OPTIONS[1:]):
            x = _array([dict(board=board)], counts)
            anchor = _prediction(self.anchor.trees[query], x, counts, "anchor")
            residual = _prediction(self.trees[query], x, counts, "residual")
            vectors = _reconstruct(anchor, residual)[0]
            counts["reconstructed_output_vectors"] += 4
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
        return dict(schema="acfqp.centered_terminal_fragments.v85", checkpoint=self.checkpoint,
            options=list(OPTIONS), queries=deepcopy(QUERIES), feature_names=list(FEATURE_NAMES),
            output_names=list(OUTPUT_NAMES), tree_parameters=dict(TREE_PARAMETERS),
            min_samples_leaf_unit="roots", trees=deepcopy(self.trees), anchor=self.anchor.to_payload())

    @classmethod
    def from_payload(cls, payload):
        return cls(deepcopy(payload["trees"]), payload["checkpoint"],
                   JointSelector.from_payload(payload["anchor"]))
