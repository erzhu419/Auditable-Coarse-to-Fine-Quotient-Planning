"""Fixed teacher-state collection and exact ranking metrics for V49."""
from __future__ import annotations

import math
import time

import numpy as np

from .lmta_aim_v43 import AIMEnvironment


def score_targets(graph, statuses):
    """The V44 score for every node, including nodes masked out of selection."""
    return np.asarray([
        math.fsum(1. / graph.in_degree(target)
                  for target in graph.successors(node) if statuses[target] == 0)
        for node in range(len(graph))], dtype=np.float64)


def features_from_state(statuses, remaining_days, remaining_budget, budget=70,
                        horizon=10):
    """Reconstruct exactly the five columns used by AIMEnvironment.features."""
    statuses = np.asarray(statuses)
    result = np.zeros((len(statuses), 5), dtype=np.float32)
    result[np.arange(len(statuses)), statuses] = 1.
    result[:, 3] = remaining_days / horizon
    result[:, 4] = remaining_budget / budget if budget else 0.
    return result


def collect_episode(graph, graph_id, seed, budget=70, horizon=10):
    """Collect one pre-selection state per actual average-score teacher action."""
    started = time.perf_counter()
    env = AIMEnvironment(graph, budget=budget, horizon=horizon, seed=seed)
    samples, days, selected_nodes = [], [], []
    while not env.done:
        cap = min(env.remaining_budget, int(env.legal_mask().sum()))
        allocated = (cap if env.remaining_days == 1 else
                     min(cap, math.ceil(env.remaining_budget / env.remaining_days)))
        selected = []
        for _ in range(allocated):
            targets = score_targets(env.graph, env.statuses)
            samples.append({"statuses": env.statuses.copy(), "day": env.day,
                            "remaining_budget": env.remaining_budget,
                            "targets": targets})
            legal = np.flatnonzero(env.legal_mask())
            node = int(legal[np.argmax(targets[legal])])
            env.select(node, phase="collection")
            selected.append(node)
        _, _, _, info = env.finish_day(phase="collection")
        days.append({"day": env.day - 1, **info})
        selected_nodes.append(selected)
    event = {"graph_id": graph_id, "environment_seed": seed,
             "raw_return": float(sum(day["day_reward"] for day in days)),
             "counters": dict(env.counters["collection"]), "day_history": days,
             "selected_nodes": selected_nodes, "state_count": len(samples),
             "label_calls": len(samples),
             "label_node_evaluations": len(samples) * len(graph),
             "wall_seconds": time.perf_counter() - started}
    return samples, event


def ranking_metrics(predictions, targets, legal):
    """Score the legal argmax and every non-tied unordered teacher-score pair."""
    predictions, targets = np.asarray(predictions), np.asarray(targets)
    indices = np.flatnonzero(legal)
    predicted_node = int(indices[np.argmax(predictions[indices])])
    teacher_node = int(indices[np.argmax(targets[indices])])
    best_score, chosen_score = float(targets[teacher_node]), float(targets[predicted_node])
    regret = best_score - chosen_score
    left, right = np.triu_indices(len(indices), k=1)
    target_difference = targets[indices[left]] - targets[indices[right]]
    prediction_difference = predictions[indices[left]] - predictions[indices[right]]
    non_ties = np.abs(target_difference) > 1e-9
    correct = np.sign(prediction_difference[non_ties]) == np.sign(target_difference[non_ties])
    prediction_ties = prediction_difference[non_ties] == 0
    return {"predicted_node": predicted_node, "teacher_node": teacher_node,
            "best_score": best_score, "chosen_score": chosen_score,
            "score_regret": regret,
            "relative_regret": regret / best_score if best_score else 0.,
            "optimal": bool(regret <= 1e-9),
            "pairwise_correct": float(correct.sum() + .5 * prediction_ties.sum()),
            "pairwise_pairs": int(non_ties.sum())}
