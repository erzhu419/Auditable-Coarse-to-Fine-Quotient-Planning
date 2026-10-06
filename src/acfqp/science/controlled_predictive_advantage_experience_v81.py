"""Paired first-action terminal advantages under one unchanged continuation policy."""
from __future__ import annotations

from collections import Counter
import random
from time import perf_counter

from acfqp.science.controlled_predictive_decision_experience_v78 import rollout_from_board


QUERIES = ("reward", "risk_goal")


def sample_root(root, parent, rule, lifecycle, iteration, root_index,
                replicas=2, max_steps=2000):
    """Sample every legal first action with paired environment and model streams.

    The first action is forced once. Every subsequent decision uses ``parent``.
    Returns include the first action's reward. Each alternative's terminal
    consequence is differenced against the reference within each replica before
    averaging. A cutoff in any trajectory censors the whole root's labels while
    preserving all raw trajectories and work.
    """
    if replicas <= 0:
        raise ValueError("replicas must be positive")
    started = perf_counter()
    board = tuple(root["board"])
    query_index = QUERIES.index(root["query"])
    known_model_counts = Counter()
    status, moves = rule.classify(board, known_model_counts)
    actions = sorted(action for action, _, _ in moves)
    reference = root["reference_action"]
    if status != "ACTIVE" or reference not in actions:
        raise ValueError("root must be ACTIVE and its reference action legal")
    ground_work, continuation_work, outcomes = Counter(), Counter(), Counter()
    raw, games = [], {}
    for replica in range(replicas):
        env_seed = (8_110_000_000 + lifecycle * 10_000_000
                    + iteration * 1_000_000 + query_index * 100_000
                    + root_index * 100 + replica)
        model_seed = env_seed + 1_000_000_000_000
        for action in actions:
            model_rng = random.Random(model_seed)
            trajectory_work = Counter()

            def actor(current, step_index):
                if step_index == 0:
                    return action
                return parent.choose(current, root["query"], rule, model_rng,
                                     work=trajectory_work)["action"]

            game = rollout_from_board(board, env_seed, actor, max_steps=max_steps)
            games[(replica, action)] = game
            ground_work.update(game["work"])
            continuation_work.update(trajectory_work)
            outcomes[game["status"]] += 1
            raw.append(dict(query=root["query"], episode=root["episode"],
                root_index=root_index, iteration=iteration, action=action,
                replica=replica, env_seed=env_seed, model_seed=model_seed,
                continuation_work=dict(trajectory_work), game=game))

    censored = bool(outcomes["CUTOFF"])
    rows, pair_deltas = [], {}
    if not censored:
        for action in actions:
            if action == reference:
                continue
            deltas = []
            for replica in range(replicas):
                candidate, baseline = games[(replica, action)], games[(replica, reference)]
                deltas.append([
                    (candidate["return_score"] - baseline["return_score"]) / 2048,
                    float(candidate["status"] == "LOST") - float(baseline["status"] == "LOST"),
                    float(candidate["status"] == "WON") - float(baseline["status"] == "WON"),
                ])
            pair_deltas[action] = deltas
            rows.append(dict(board=list(board), query=root["query"],
                reference_action=reference, action=action,
                target=[sum(delta[index] for delta in deltas) / replicas
                        for index in range(3)], episode=root["episode"],
                iteration=iteration, step=root["step"], root_index=root_index,
                replicas=replicas))
    log = dict(roots=1, trajectories=len(raw), rows=len(rows), censored_root=censored,
        outcomes=dict(outcomes), ground_work=dict(ground_work),
        continuation_work=dict(continuation_work), known_model_counts=dict(known_model_counts),
        work=dict(ground=dict(ground_work), continuation=dict(continuation_work),
                  known_model=dict(known_model_counts)),
        model_rng_streams=len(raw),
        model_uniform_draws=continuation_work.get("model_uniform_draws", 0),
        pair_deltas=pair_deltas, seconds=perf_counter() - started)
    return rows, raw, log
