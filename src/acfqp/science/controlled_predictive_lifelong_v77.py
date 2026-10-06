"""Fixed-algorithm accumulation of policy-conditioned planning consequences.

Each tree predicts one executable policy's reward, first failure, and first
success together. REVISED can change the partition of a fixed feature space;
it does not invent features, policies, or transition mechanisms. Episodes with
index 4 modulo 5 are internal validation and never supply leaf statistics.
"""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
from time import perf_counter

import numpy as np


POLICIES = ("GREEDY", "SPACE", "SNAKE")
MODES = ("FROZEN", "FIXED", "REVISED")
FEATURE_NAMES = tuple(f"rank_{i}" for i in range(16)) + (
    "empty_fraction", "maximum_rank", "corner_maximum_fraction", "equal_edge_fraction",
) + tuple(f"{axis}_{i}_{stat}" for axis in ("row", "column") for i in range(4)
          for stat in ("nonzero_fraction", "packed_equal_fraction")) + ("horizon",)
_EDGES = tuple((i, i + d) for i in range(16) for d in (1, 4)
               if (d == 1 and i % 4 < 3) or (d == 4 and i < 12))


def features(board, horizon):
    """Observed afterstate summaries, with no spawn enumeration or rollout."""
    board = tuple(board)
    maximum = max(board)
    result = [rank / 11 for rank in board]
    result.extend((board.count(0) / 16, maximum / 11,
        sum(board[i] == maximum for i in (0, 3, 12, 15)) / 4,
        sum(board[i] != 0 and board[i] == board[j] for i, j in _EDGES) / 24))
    lines = [board[4 * i:4 * i + 4] for i in range(4)]
    lines += [board[i::4] for i in range(4)]
    for line in lines:
        packed = [rank for rank in line if rank]
        result.extend((len(packed) / 4,
                       sum(a == b for a, b in zip(packed, packed[1:])) / 3))
    result.append(horizon / 32)
    return tuple(result)


def _arrays(records, counts):
    counts["feature_rows"] += len(records)
    x = np.asarray([features(row["board"], row["horizon"]) for row in records], dtype=np.float32)
    x = x.reshape((-1, len(FEATURE_NAMES)))
    y = np.asarray([row["target"] for row in records], dtype=float).reshape((-1, 3))
    return x, y


def _fit(x, y, counts):
    from sklearn.tree import DecisionTreeRegressor

    estimator = DecisionTreeRegressor(max_depth=8, min_samples_leaf=16, random_state=7701)
    estimator.fit(x, y)
    counts["tree_fits"] += 1
    counts["fit_rows"] += len(x)
    tree = estimator.tree_
    return dict(left=tree.children_left.tolist(), right=tree.children_right.tolist(),
        feature=tree.feature.tolist(), threshold=tree.threshold.tolist(),
        values=tree.value[:, :, 0].tolist(), samples=tree.n_node_samples.tolist())


def _apply(tree, x, counts):
    """Batch interpretation of a JSON tree using float32 input features."""
    nodes = np.zeros(len(x), dtype=np.int64)
    left = np.asarray(tree["left"], dtype=np.int64)
    right = np.asarray(tree["right"], dtype=np.int64)
    split_feature = np.asarray(tree["feature"], dtype=np.int64)
    threshold = np.asarray(tree["threshold"], dtype=float)
    active = np.flatnonzero(left[nodes] >= 0)
    counts["tree_apply_rows"] += len(x)
    while len(active):
        here = nodes[active]
        choose_left = x[active, split_feature[here]] <= threshold[here]
        nodes[active] = np.where(choose_left, left[here], right[here])
        counts["tree_split_visits"] += len(active)
        active = active[left[nodes[active]] >= 0]
    return nodes


def _predict(tree, x, counts):
    return np.asarray(tree["values"], dtype=float)[_apply(tree, x, counts)]


def _refresh_leaves(tree, x, y, counts):
    leaves = _apply(tree, x, counts)
    changed = touched = 0
    # Unvisited leaves retain their previous values; no holdout row enters here.
    for leaf in np.unique(leaves):
        selected = leaves == leaf
        values = np.mean(y[selected], axis=0).tolist()
        changed += values != tree["values"][leaf]
        tree["values"][leaf] = values
        tree["samples"][leaf] = int(np.sum(selected))
        touched += 1
    counts["leaf_stat_rows"] += len(x)
    counts["leaf_stats_updated"] += touched
    counts["leaf_values_changed"] += changed
    return dict(leaves_updated=touched, leaf_values_changed=changed)


def _structure(tree):
    return {key: tree[key] for key in ("left", "right", "feature", "threshold")}


def _structure_changes(old, new):
    # Node-index comparisons describe implementation work, not semantic distance.
    old_splits = [(i, f, old["threshold"][i]) for i, f in enumerate(old["feature"])
                  if old["left"][i] >= 0]
    new_splits = [(i, f, new["threshold"][i]) for i, f in enumerate(new["feature"])
                  if new["left"][i] >= 0]
    return dict(structure_changed=_structure(old) != _structure(new),
        old_nodes=len(old["left"]), new_nodes=len(new["left"]),
        old_leaves=sum(i < 0 for i in old["left"]),
        new_leaves=sum(i < 0 for i in new["left"]),
        split_nodes_changed=len(set(old_splits).symmetric_difference(new_splits)))


class Knowledge:
    def __init__(self, mode, trees, checkpoint, counts=None):
        self.mode = mode
        self.trees = trees
        self.checkpoint = checkpoint
        self.counts = Counter(counts or {})

    @classmethod
    def initialize(cls, records):
        """Fit one common warmup model, then give each mode an independent copy.

        Return ``(knowledge_by_mode, common_log)``. The common warmup cost is
        measured once and must be attributed to every learned method.
        """
        started = perf_counter()
        records = list(records)
        counts = Counter(metadata_rows_read=len(records))
        checkpoint = 1 + max(row["episode"] for row in records)
        trees = {}
        policy_logs = {}
        for policy in POLICIES:
            training = [row for row in records
                        if row["policy"] == policy and row["episode"] % 5 != 4]
            if not training:
                raise ValueError(f"warmup has no training rows for {policy}")
            counts["training_rows_read"] += len(training)
            x, y = _arrays(training, counts)
            trees[policy] = _fit(x, y, counts)
            policy_logs[policy] = dict(training_rows=len(training),
                heldout_rows=sum(row["policy"] == policy and row["episode"] % 5 == 4
                                 for row in records),
                nodes=len(trees[policy]["left"]),
                leaves=sum(i < 0 for i in trees[policy]["left"]))
        knowledge = {mode: cls(mode, deepcopy(trees), checkpoint) for mode in MODES}
        return knowledge, dict(checkpoint=checkpoint, counts=dict(counts), policies=policy_logs,
                               seconds=perf_counter() - started)

    def update(self, all_records, previous_checkpoint):
        """Accumulate a chronological batch; only REVISED may replace topology.

        Checkpoints count episodes: records with ``episode < previous_checkpoint``
        belong to the previous prefix. Both old and new held-out observations
        are required before accepting a partition proposal.
        """
        started = perf_counter()
        if previous_checkpoint != self.checkpoint:
            raise ValueError("previous_checkpoint must equal the current episode count")
        records = list(all_records)
        before = self.counts.copy()
        self.counts["metadata_rows_read"] += len(records)
        checkpoint = 1 + max(row["episode"] for row in records)
        if checkpoint <= previous_checkpoint:
            raise ValueError("update requires a newly observed episode batch")
        policy_logs = {}
        if self.mode != "FROZEN":
            for policy in POLICIES:
                rows = [row for row in records if row["policy"] == policy]
                training = [row for row in rows if row["episode"] % 5 != 4]
                self.counts["training_rows_read"] += len(training)
                x, y = _arrays(training, self.counts)
                incumbent = self.trees[policy]
                log = _refresh_leaves(incumbent, x, y, self.counts)
                log["training_rows"] = len(training)
                if self.mode == "REVISED":
                    candidate = _fit(x, y, self.counts)
                    log.update(_structure_changes(incumbent, candidate))
                    losses = {}
                    sizes = {}
                    for name, is_old in (("old", True), ("new", False)):
                        validation = [row for row in rows if row["episode"] % 5 == 4
                                      and (row["episode"] < previous_checkpoint) == is_old]
                        sizes[name] = len(validation)
                        self.counts["validation_rows_read"] += len(validation)
                        vx, vy = _arrays(validation, self.counts)
                        losses[name] = dict(incumbent=None, candidate=None)
                        if len(validation):
                            for label, tree in (("incumbent", incumbent), ("candidate", candidate)):
                                error = _predict(tree, vx, self.counts) - vy
                                losses[name][label] = float(np.mean(error * error))
                    accepted = bool(sizes["old"] and sizes["new"] and
                        losses["new"]["candidate"] < losses["new"]["incumbent"] and
                        losses["old"]["candidate"] <= losses["old"]["incumbent"] * 1.02 + 1e-12)
                    log.update(validation_rows=sizes, validation_mse=losses, accepted=accepted)
                    self.counts["proposals_accepted" if accepted else "proposals_rejected"] += 1
                    if accepted:
                        self.trees[policy] = candidate
                        self.counts["accepted_structure_changes"] += log["structure_changed"]
                        self.counts["accepted_split_nodes_changed"] += log["split_nodes_changed"]
                policy_logs[policy] = log
        self.checkpoint = checkpoint
        delta = {key: self.counts[key] - before[key] for key in self.counts
                 if self.counts[key] != before[key]}
        return dict(mode=self.mode, previous_checkpoint=previous_checkpoint, checkpoint=checkpoint,
                    policies=policy_logs, counts=delta, seconds=perf_counter() - started)

    def predict_many(self, boards, horizon):
        """Return N x policy x (reward, failure, success) paired predictions."""
        boards = list(boards)
        self.counts["prediction_boards"] += len(boards)
        self.counts["feature_rows"] += len(boards)
        self.counts["policy_prediction_rows"] += len(boards) * len(POLICIES)
        x = np.asarray([features(board, horizon) for board in boards], dtype=np.float32)
        x = x.reshape((-1, len(FEATURE_NAMES)))
        return np.stack([_predict(self.trees[policy], x, self.counts) for policy in POLICIES], axis=1)

    def to_payload(self):
        return dict(schema="acfqp.lifelong_consequences.v77", mode=self.mode,
            checkpoint=self.checkpoint, policies=list(POLICIES), feature_names=list(FEATURE_NAMES),
            tree_parameters=dict(max_depth=8, min_samples_leaf=16, random_state=7701),
            trees=deepcopy(self.trees), counts=dict(self.counts))

    @classmethod
    def from_payload(cls, payload):
        return cls(payload["mode"], deepcopy(payload["trees"]), payload["checkpoint"], payload["counts"])
