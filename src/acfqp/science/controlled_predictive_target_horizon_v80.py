"""Paired finite-window and terminal consequences from identical observations.

Both models use the same afterstate features, rows, policy binding and fitting
recipe. Only the consequence target changes. A terminal target means following
the named fixed policy to the observed terminal event; it is not a guarantee
about the planner's later replanning decisions.
"""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
from time import perf_counter

import numpy as np

from acfqp.science.controlled_predictive_lifelong_v77 import (
    FEATURE_NAMES, POLICIES, _fit, _predict, features,
)


FEATURE_CONTEXT_HORIZON = 30
TARGET_SCOPES = ("SHORT", "TERMINAL")
TARGET_SEMANTICS = {
    "SHORT": "Policy-conditioned next 30 action rewards and first terminal event, starting at anchor spawn; anchor action reward excluded.",
    "TERMINAL": "Policy-conditioned rewards through observed WON or LOST and its terminal indicator, starting at anchor spawn; anchor action reward excluded. Horizon 30 is only the common leaf feature context.",
}


def paired_targets(game, policy, episode_index, stride=4, anchor_only=False):
    """Return one row carrying both targets, or discard a nonterminal game.

    Each anchor is the afterstate before its spawn. The terminal event at that
    spawn is included, while reward starts with the next action. Both targets
    therefore describe consequences after the same already-scored action.
    """
    if stride <= 0:
        raise ValueError("stride must be positive")
    if policy not in POLICIES:
        raise ValueError(f"unknown continuation policy {policy}")
    steps = game["steps"]
    anchors = ([0] if anchor_only else
               sorted(set(range(0, len(steps), stride)) | {len(steps) - 1})) if steps else []
    log = dict(episode=episode_index, policy=policy, input_steps=len(steps),
        status=game["status"], anchor_only=anchor_only, candidate_anchors=len(anchors),
        paired_records=0, discarded_records=0, discarded_game=False,
        discard_reason=None, short_terminal_records=0, terminal_records=0,
        short_success_records=0, terminal_success_records=0)
    if game["status"] not in ("WON", "LOST"):
        log.update(discarded_game=True, discarded_records=len(anchors),
                   discard_reason="no_observed_terminal")
        return [], log
    if not steps:
        return [], log
    terminal_index = next(index for index, step in enumerate(steps)
                          if step["status"] in ("WON", "LOST"))
    terminal_status = steps[terminal_index]["status"]
    cumulative = [0]
    for step in steps:
        cumulative.append(cumulative[-1] + step["score"])
    rows = []
    for anchor in anchors:
        if anchor > terminal_index:
            continue
        short_end = min(anchor + FEATURE_CONTEXT_HORIZON, terminal_index)
        short_terminal = short_end == terminal_index
        terminal = [
            (cumulative[terminal_index + 1] - cumulative[anchor + 1]) / 2048,
            float(terminal_status == "LOST"), float(terminal_status == "WON"),
        ]
        short = [
            (cumulative[short_end + 1] - cumulative[anchor + 1]) / 2048,
            float(short_terminal and terminal_status == "LOST"),
            float(short_terminal and terminal_status == "WON"),
        ]
        rows.append(dict(board=list(steps[anchor]["afterstate"]), episode=episode_index,
            anchor_step=anchor, policy=policy, short_target=short, terminal_target=terminal))
        log["short_terminal_records"] += int(short_terminal)
        log["short_success_records"] += int(short[2])
        log["terminal_success_records"] += int(terminal[2])
    log.update(paired_records=len(rows), terminal_records=len(rows))
    return rows, log


def _feature_array(rows, counts):
    counts["feature_rows"] += len(rows)
    return np.asarray([features(row["board"], FEATURE_CONTEXT_HORIZON) for row in rows],
                      dtype=np.float32).reshape((-1, len(FEATURE_NAMES)))


class ConsequenceModel:
    """Three policy-bound vector trees, with explicit target-horizon semantics."""

    def __init__(self, target_scope, trees, checkpoint, counts=None):
        if target_scope not in TARGET_SCOPES:
            raise ValueError(f"unknown target scope {target_scope}")
        self.target_scope = target_scope
        self.trees = trees
        self.checkpoint = checkpoint
        self.counts = Counter(counts or {})

    def predict_many(self, boards, horizon):
        """Return N x policy x (reward, failure, success) for the shared leaf context.

        For TERMINAL, ``horizon=30`` selects the common input context, not a
        truncation of the target. V77's depth-two planner supplies this context.
        """
        if horizon != FEATURE_CONTEXT_HORIZON:
            raise ValueError("V80 requires the common leaf feature context horizon=30")
        boards = list(boards)
        self.counts["prediction_boards"] += len(boards)
        self.counts["policy_prediction_rows"] += len(boards) * len(POLICIES)
        x = _feature_array([dict(board=board) for board in boards], self.counts)
        return np.stack([_predict(self.trees[policy], x, self.counts)
                         for policy in POLICIES], axis=1)

    def to_payload(self):
        return dict(schema="acfqp.paired_target_consequences.v80", target_scope=self.target_scope,
            target_semantics=TARGET_SEMANTICS[self.target_scope],
            feature_context_horizon=FEATURE_CONTEXT_HORIZON, checkpoint=self.checkpoint,
            policies=list(POLICIES), feature_names=list(FEATURE_NAMES),
            tree_parameters=dict(max_depth=8, min_samples_leaf=16, random_state=7701),
            trees=deepcopy(self.trees), counts=dict(self.counts))

    @classmethod
    def from_payload(cls, payload):
        if payload["feature_context_horizon"] != FEATURE_CONTEXT_HORIZON:
            raise ValueError("V80 model requires feature_context_horizon=30")
        return cls(payload["target_scope"], deepcopy(payload["trees"]),
                   payload["checkpoint"], payload["counts"])


def fit_model(rows, checkpoint, target_scope):
    """Fit the fixed recipe on one chronological prefix, without holdout leakage.

    Row order within each policy is preserved for both scopes. Internal holdout
    error is diagnostic only and never selects or rejects a fitted model.
    """
    if target_scope not in TARGET_SCOPES:
        raise ValueError(f"unknown target scope {target_scope}")
    started = perf_counter()
    rows = list(rows)
    prefix = [row for row in rows if row["episode"] < checkpoint]
    counts = Counter(metadata_rows_read=len(rows))
    target_key = target_scope.lower() + "_target"
    trees, policy_logs = {}, {}
    for policy in POLICIES:
        policy_rows = [row for row in prefix if row["policy"] == policy]
        training = [row for row in policy_rows if row["episode"] % 5 != 4]
        holdout = [row for row in policy_rows if row["episode"] % 5 == 4]
        if not training:
            raise ValueError(f"prefix has no training rows for {policy}")
        counts["training_rows_read"] += len(training)
        x = _feature_array(training, counts)
        y = np.asarray([row[target_key] for row in training], dtype=float)
        tree = trees[policy] = _fit(x, y, counts)
        mse = None
        if holdout:
            counts["validation_rows_read"] += len(holdout)
            vx = _feature_array(holdout, counts)
            vy = np.asarray([row[target_key] for row in holdout], dtype=float)
            error = _predict(tree, vx, counts) - vy
            mse = np.mean(error * error, axis=0).tolist()
        policy_logs[policy] = dict(training_rows=len(training), heldout_rows=len(holdout),
            nodes=len(tree["left"]), leaves=sum(index < 0 for index in tree["left"]),
            training_target_mean=np.mean(y, axis=0).tolist(), heldout_mse_components=mse)
    model = ConsequenceModel(target_scope, trees, checkpoint, counts)
    log = dict(target_scope=target_scope, checkpoint=checkpoint,
        feature_context_horizon=FEATURE_CONTEXT_HORIZON,
        target_semantics=TARGET_SEMANTICS[target_scope], input_records=len(rows),
        prefix_records=len(prefix), future_records_excluded=len(rows) - len(prefix),
        training_records=sum(row["episode"] % 5 != 4 for row in prefix),
        heldout_records=sum(row["episode"] % 5 == 4 for row in prefix),
        policies=policy_logs, counts=dict(counts), seconds=perf_counter() - started)
    return model, log
