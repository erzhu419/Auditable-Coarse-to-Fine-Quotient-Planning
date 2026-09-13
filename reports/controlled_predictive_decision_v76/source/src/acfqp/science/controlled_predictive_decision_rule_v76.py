"""Source-trained, query-conditioned action scoring with a portable tree.

Feature extraction uses only the observed board and four learned deterministic
swipes. The exported predictor needs only the standard library; sklearn is
loaded only by fit(). No spawn support or target model is consulted.
"""
from __future__ import annotations

from collections import Counter
from struct import pack, unpack
from time import perf_counter


BASE_FEATURE_NAMES = (
    "current_empties", "current_max_rank", "current_goal_gap", "current_total_value",
    "current_max_count", "current_corner_max_fraction", "current_equal_edges", "current_equal_edge_value",
    "after_empties", "after_max_rank", "after_goal_gap", "after_max_count",
    "after_corner_max_fraction", "after_equal_edges", "after_equal_edge_value",
    "action_merge_reward", "action_changed_cells", "after_goal_reached",
    "along_packed_equal_pairs", "along_once_merge_count", "along_once_merge_reward",
    "across_packed_equal_pairs", "across_once_merge_count", "across_once_merge_reward",
    "along_empty_mean", "along_empty_variance", "across_empty_mean", "across_empty_variance",
    "empty_neighbor_rank1", "empty_neighbor_rank2",
)
QUERY_FEATURE_NAMES = (
    "risk_per_reward", "goal_per_reward", "risk_x_after_empties", "risk_x_after_equal_edges",
    "risk_x_after_equal_edge_value", "risk_x_empty_neighbor_rank1", "risk_x_empty_neighbor_rank2",
    "goal_x_after_goal_reached", "goal_x_after_goal_proximity", "goal_x_action_merge_reward",
    "risk_x_action_merge_reward",
)
FEATURE_NAMES = BASE_FEATURE_NAMES + QUERY_FEATURE_NAMES
_INDEX = {name: index for index, name in enumerate(BASE_FEATURE_NAMES)}
_EDGES = tuple((cell, cell + delta) for cell in range(16) for delta in (1, 4)
               if (delta == 1 and cell % 4 < 3) or (delta == 4 and cell < 12))
_NEIGHBORS = tuple(tuple(b if a == cell else a for a, b in _EDGES if a == cell or b == cell)
                   for cell in range(16))


def _summary(board, goal, work):
    maximum = max(board)
    max_count = board.count(maximum)
    equal_edges = equal_value = 0
    for left, right in _EDGES:
        work["feature_adjacency_tests"] += 1
        if board[left] and board[left] == board[right]:
            equal_edges += 1
            equal_value += 1 << (board[left] + 1)
    return (board.count(0), maximum, goal - maximum,
            sum(1 << rank for rank in board if rank) / 2048,
            max_count, sum(board[cell] == maximum for cell in (0, 3, 12, 15)) / max_count,
            equal_edges, equal_value / 2048)


def _line_features(lines, work):
    pairs = merges = reward = 0
    empty = []
    for line in lines:
        work["feature_line_summaries"] += 1
        values = tuple(rank for rank in line if rank)
        empty.append(4 - len(values))
        for left, right in zip(values, values[1:]):
            work["feature_line_pair_tests"] += 1
            pairs += left == right
        position = 0
        while position + 1 < len(values):
            work["feature_once_merge_tests"] += 1
            if values[position] == values[position + 1]:
                merges += 1
                reward += 1 << (values[position] + 1)
                position += 2
            else:
                position += 1
    mean = sum(empty) / 4
    return (pairs, merges, reward / 2048), (mean, sum((value - mean) ** 2 for value in empty) / 4)


def features(board, rule, work=None):
    """Return features for legal actions; action names are not input features."""
    if work is None:
        work = Counter()
    work["feature_boards"] += 1
    board = tuple(board)
    _, moves = rule.classify(board, work)
    if not moves:
        return {}
    current = _summary(board, rule.goal_rank, work)
    result = {}
    for action, after, score in moves:
        work["feature_actions"] += 1
        summary = _summary(after, rule.goal_rank, work)
        rows = tuple(tuple(after[4 * row:4 * row + 4]) for row in range(4))
        columns = tuple(tuple(after[4 * row + column] for row in range(4)) for column in range(4))
        along, across = (columns, rows) if action in ("UP", "DOWN") else (rows, columns)
        along_potential, along_empty = _line_features(along, work)
        across_potential, across_empty = _line_features(across, work)
        neighbors = Counter()
        for cell, rank in enumerate(after):
            if rank == 0:
                for neighbor in _NEIGHBORS[cell]:
                    work["feature_empty_neighbor_reads"] += 1
                    neighbors[after[neighbor]] += 1
        # Total tile value is unchanged by a swipe, so it is represented once.
        result[action] = tuple(float(value) for value in
            (current + summary[:3] + summary[4:] +
             (score / 2048, sum(left != right for left, right in zip(board, after)),
              int(summary[1] >= rule.goal_rank)) +
             along_potential + across_potential + along_empty + across_empty +
             (neighbors[1], neighbors[2])))
    return result


def query_features(base, query):
    """Positive scaling of all query weights leaves the feature vector equal."""
    reward = float(query.get("reward_weight", 1))
    risk = float(query.get("failure_penalty", 0)) / reward
    goal = float(query.get("goal_bonus", 0)) / reward
    def value(name):
        return base[_INDEX[name]]
    proximity = value("after_max_rank") / (value("after_max_rank") + value("after_goal_gap"))
    return tuple(base) + (risk, goal, risk * value("after_empties") / 16,
        risk * value("after_equal_edges") / 24, risk * value("after_equal_edge_value"),
        risk * value("empty_neighbor_rank1") / 48, risk * value("empty_neighbor_rank2") / 48,
        goal * value("after_goal_reached"), goal * proximity,
        goal * value("action_merge_reward"), risk * value("action_merge_reward"))


def predict_probability(payload, vector, work=None):
    """Interpret the exported tree with sklearn-compatible float32 inputs."""
    tree = payload["tree"]
    node = 0
    while tree["left"][node] >= 0:
        feature = tree["feature"][node]
        value = unpack("f", pack("f", float(vector[feature])))[0]
        if work is not None:
            work["tree_decisions"] += 1
            work["float32_feature_conversions"] += 1
        node = tree["left"][node] if value <= tree["threshold"][node] else tree["right"][node]
    if work is not None:
        work["tree_predictions"] += 1
    return tree["p_optimal"][node]


def score_actions(payload, action_features, query, work=None):
    return {action: predict_probability(payload, query_features(action_features[action], query), work)
            for action in sorted(action_features)}


def choose_action(payload, action_features, query, work=None):
    scores = score_actions(payload, action_features, query, work)
    return min(scores, key=lambda action: (-scores[action], action)) if scores else None


def fit(records):
    """Fit exactly the frozen depth-8/leaf-16 tree; records contain features and label."""
    started = perf_counter()
    import numpy as np
    from sklearn.tree import DecisionTreeClassifier

    records = tuple(records)
    x = np.asarray([row["features"] for row in records], dtype=np.float32)
    y = np.asarray([row["label"] for row in records], dtype=np.int64)
    if x.shape[1] != len(FEATURE_NAMES):
        raise ValueError("training feature columns disagree with the fixed V76 feature list")
    estimator = DecisionTreeClassifier(max_depth=8, min_samples_leaf=16, random_state=7601)
    estimator.fit(x, y)
    tree = estimator.tree_
    classes = list(estimator.classes_)
    positive = classes.index(1) if 1 in classes else None
    probabilities = [float(values[0][positive] / sum(values[0])) if positive is not None else 0.0
                     for values in tree.value]
    return dict(schema="acfqp.decision_rule.v76", feature_names=list(FEATURE_NAMES),
        base_feature_names=list(BASE_FEATURE_NAMES),
        training=dict(max_depth=8, min_samples_leaf=16, random_state=7601,
            records=len(records), optimal_labels=int(sum(y)), nonoptimal_labels=int(len(y) - sum(y)),
            nodes=int(tree.node_count), leaves=int(estimator.get_n_leaves()), depth=int(estimator.get_depth())),
        tree=dict(left=tree.children_left.tolist(), right=tree.children_right.tolist(),
            feature=tree.feature.tolist(), threshold=tree.threshold.tolist(), p_optimal=probabilities,
            samples=tree.n_node_samples.tolist()),
        feature_importance=estimator.feature_importances_.tolist(),
        fit_seconds=perf_counter() - started)
