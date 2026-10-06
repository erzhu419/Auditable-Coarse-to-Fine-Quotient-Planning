"""Policy iteration from paired terminal action consequences.

Each learned layer estimates the advantage of a legal first action relative to
its unchanged parent policy's action. All three consequences share one leaf;
the reference action has exact zero advantage. Predictions do not consume RNG.
"""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
from time import perf_counter

import numpy as np

from acfqp.science.controlled_predictive_lifelong_v77 import (
    FEATURE_NAMES as BOARD_FEATURE_NAMES, _predict, features,
)
from acfqp.science import controlled_predictive_lifelong_planner_v77 as planner


ACTIONS = ("DOWN", "LEFT", "RIGHT", "UP")
QUERIES = {
    "reward": dict(reward_weight=1.0, failure_penalty=0.0, goal_bonus=0.0),
    "risk_goal": dict(reward_weight=1.0, failure_penalty=4.0, goal_bonus=4.0),
}
FEATURE_NAMES = (
    tuple("state_" + name for name in BOARD_FEATURE_NAMES[:-1])
    + tuple("afterstate_difference_" + name for name in BOARD_FEATURE_NAMES[:-1])
    + ("immediate_reward_difference",)
    + tuple("candidate_" + action for action in ACTIONS)
    + tuple("reference_" + action for action in ACTIONS)
)
TREE_PARAMETERS = dict(max_depth=4, min_samples_leaf=8, random_state=8101)


def _merge(work, counts):
    if work is not None:
        for key, value in counts.items():
            work[key] = work.get(key, 0) + value


def _value(vector, query):
    return (query["reward_weight"] * vector[0]
            - query["failure_penalty"] * vector[1]
            + query["goal_bonus"] * vector[2])


def action_features(board, action, reference_action, rule, work=None):
    """81 observed-state and deterministic afterstate features, without sampling."""
    counts = Counter()
    candidate, reward, changed = rule.swipe(board, action, counts)
    reference, reference_reward, reference_changed = rule.swipe(board, reference_action, counts)
    if not changed or not reference_changed:
        raise ValueError("advantage features require legal candidate and reference actions")
    state_features = features(board, 30)[:-1]
    candidate_features = features(candidate, 30)[:-1]
    reference_features = features(reference, 30)[:-1]
    result = (state_features
        + tuple(a - b for a, b in zip(candidate_features, reference_features))
        + ((reward - reference_reward) / 2048,)
        + tuple(float(action == choice) for choice in ACTIONS)
        + tuple(float(reference_action == choice) for choice in ACTIONS))
    counts["advantage_feature_rows"] += 1
    counts["board_feature_rows"] += 3
    _merge(work, counts)
    return result


def _array(rows, rule, counts):
    return np.asarray([action_features(row["board"], row["action"],
        row["reference_action"], rule, counts) for row in rows],
        dtype=np.float32).reshape((-1, len(FEATURE_NAMES)))


def _fit(x, y, counts):
    from sklearn.tree import DecisionTreeRegressor

    estimator = DecisionTreeRegressor(**TREE_PARAMETERS).fit(x, y)
    counts["tree_fits"] += 1
    counts["fit_rows"] += len(x)
    tree = estimator.tree_
    return dict(left=tree.children_left.tolist(), right=tree.children_right.tolist(),
        feature=tree.feature.tolist(), threshold=tree.threshold.tolist(),
        values=tree.value[:, :, 0].tolist(), samples=tree.n_node_samples.tolist())


class Policy:
    """An immutable-in-use policy chain ending in the common sampled H2 policy."""

    def __init__(self, parent=None, trees=None, iteration=0):
        self.parent = parent
        self.trees = trees or {}
        self.iteration = iteration

    @classmethod
    def base(cls):
        return cls()

    def choose(self, board, query_name, rule, rng, work=None):
        query = QUERIES[query_name]
        counts = Counter()
        if self.parent is None:
            result = planner.choose(board, query, None, rule, rng, depth=2, work=counts)
            reference = result["action"]
            result.update(reference_action=reference, advantage=[0.0, 0.0, 0.0],
                action_advantages=({reference: dict(target=[0.0, 0.0, 0.0], value=0.0)}
                                   if reference is not None else {}), iteration=0)
            # Preserve the base planner's predicted value as a separate quantity.
            result["h2_value"] = result["value"]
            result["value"] = 0.0
        else:
            parent_result = self.parent.choose(board, query_name, rule, rng, work=counts)
            reference = parent_result["action"]
            advantages = ({reference: dict(target=[0.0, 0.0, 0.0], value=0.0)}
                          if reference is not None else {})
            chosen, best = reference, 0.0
            if reference is not None:
                _, moves = rule.classify(board, counts)
                alternatives = sorted(action for action, _, _ in moves if action != reference)
                if alternatives:
                    x = _array([dict(board=board, action=action, reference_action=reference)
                                for action in alternatives], rule, counts)
                    predictions = _predict(self.trees[query_name], x, counts)
                    counts["advantage_prediction_rows"] += len(alternatives)
                    for action, vector in zip(alternatives, predictions):
                        target = vector.tolist()
                        value = float(_value(target, query))
                        advantages[action] = dict(target=target, value=value)
                        if value > best:
                            chosen, best = action, value
                counts["learned_policy_decisions"] += 1
                counts["reference_actions_changed"] += chosen != reference
            result = dict(action=chosen, reference_action=reference,
                advantage=advantages[chosen]["target"] if chosen is not None else [0.0] * 3,
                value=best, action_advantages=advantages, iteration=self.iteration)
        result["counts"] = dict(counts)
        _merge(work, counts)
        return result

    def to_payload(self):
        return dict(schema="acfqp.terminal_policy_advantage.v81", iteration=self.iteration,
            queries=deepcopy(QUERIES), feature_names=list(FEATURE_NAMES),
            tree_parameters=dict(TREE_PARAMETERS), trees=deepcopy(self.trees),
            parent=self.parent.to_payload() if self.parent is not None else None)

    @classmethod
    def from_payload(cls, payload):
        parent = cls.from_payload(payload["parent"]) if payload["parent"] is not None else None
        return cls(parent, deepcopy(payload["trees"]), payload["iteration"])


def improve(parent, rows, iteration, rule):
    """Fit one layer on this parent's latest paired means; holdout is diagnostic.

    The caller averages repetitions within each root and alternative action.
    Rows from other iterations and reference-zero rows never enter the fit.
    No holdout result selects, changes or rejects the resulting policy.
    """
    if iteration != parent.iteration + 1:
        raise ValueError("improvement iteration must immediately follow its parent")
    started = perf_counter()
    records = list(rows)
    current = [row for row in records if row["iteration"] == iteration]
    alternatives = [row for row in current if row["action"] != row["reference_action"]]
    counts = Counter(metadata_rows_read=len(records))
    trees, query_logs = {}, {}
    for query_name in QUERIES:
        selected = [row for row in alternatives if row["query"] == query_name]
        training = [row for row in selected if row["episode"] % 5 != 4]
        heldout = [row for row in selected if row["episode"] % 5 == 4]
        if not training:
            raise ValueError(f"iteration {iteration} has no training alternatives for {query_name}")
        counts["training_rows_read"] += len(training)
        x = _array(training, rule, counts)
        y = np.asarray([row["target"] for row in training], dtype=float).reshape((-1, 3))
        tree = trees[query_name] = _fit(x, y, counts)
        mse = None
        if heldout:
            counts["validation_rows_read"] += len(heldout)
            vx = _array(heldout, rule, counts)
            vy = np.asarray([row["target"] for row in heldout], dtype=float)
            error = _predict(tree, vx, counts) - vy
            mse = np.mean(error * error, axis=0).tolist()
        query_logs[query_name] = dict(training_rows=len(training), heldout_rows=len(heldout),
            nodes=len(tree["left"]), leaves=sum(node < 0 for node in tree["left"]),
            training_target_mean=np.mean(y, axis=0).tolist(), heldout_mse_components=mse)
    policy = Policy(Policy.from_payload(parent.to_payload()), trees, iteration)
    return policy, dict(iteration=iteration, parent_iteration=parent.iteration,
        input_records=len(records), current_iteration_records=len(current),
        other_iteration_records_excluded=len(records) - len(current),
        reference_records_excluded=len(current) - len(alternatives),
        training_records=sum(row["episode"] % 5 != 4 for row in alternatives),
        heldout_records=sum(row["episode"] % 5 == 4 for row in alternatives),
        queries=query_logs, counts=dict(counts), seconds=perf_counter() - started)
