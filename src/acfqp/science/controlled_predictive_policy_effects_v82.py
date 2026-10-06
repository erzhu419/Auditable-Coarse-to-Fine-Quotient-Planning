"""Paired terminal rollouts isolating a first-action change and ongoing updating."""
from __future__ import annotations

from collections import Counter
import random
from time import perf_counter

from acfqp.science.controlled_predictive_decision_experience_v78 import rollout_from_board
from acfqp.science.controlled_predictive_policy_advantage_v81 import QUERIES


ARMS = ("PARENT", "FIRST_ONLY", "FULL_UPDATE")


def sample_triplet(root, p0, p1, rule, lifecycle, replica, max_steps=2000):
    """Keep the root decision fixed; couple all arms by both random streams.

    The recorded reference/selected action is forced at step zero without a
    policy call or model random draw. PARENT and FIRST_ONLY then follow p0;
    FULL_UPDATE follows p1. All summaries include the first action's reward.
    CUTOFF remains a censored outcome and every trajectory is retained.
    """
    started = perf_counter()
    query_name = root["query"]
    query = QUERIES[query_name]
    query_index = tuple(QUERIES).index(query_name)
    env_seed = (8_210_000_000 + lifecycle * 10_000_000
                + query_index * 100_000 + root["root_index"] * 100 + replica)
    model_seed = env_seed + 1_000_000_000_000
    ground_work, planning_counts, outcomes = Counter(), Counter(), Counter()
    games, raw = {}, []
    for method in ARMS:
        first_action = (root["reference_action"] if method == "PARENT"
                        else root["selected_action"])
        continuation = p1 if method == "FULL_UPDATE" else p0
        model_rng, work = random.Random(model_seed), Counter()

        def actor(board, step_index):
            if step_index == 0:
                return first_action
            return continuation.choose(board, query_name, rule, model_rng,
                                       work=work)["action"]

        game = rollout_from_board(tuple(root["board"]), env_seed, actor,
                                  max_steps=max_steps)
        utility = (query["reward_weight"] * game["return_score"] / 2048
                   - query["failure_penalty"] * (game["status"] == "LOST")
                   + query["goal_bonus"] * (game["status"] == "WON"))
        games[method] = dict(replica=replica, env_seed=env_seed,
            model_seed=model_seed, query=query_name, score=game["return_score"],
            status=game["status"], steps=game["steps_count"],
            max_rank=max(game["final_board"]), utility=utility,
            seconds=game["seconds"], environment_counts=game["work"],
            planning_counts=dict(work), continuation_iteration=continuation.iteration)
        raw.append(dict(method=method, game=game))
        ground_work.update(game["work"])
        planning_counts.update(work)
        outcomes[game["status"]] += 1
    log = dict(trajectories=len(raw), outcomes=dict(outcomes),
        ground_work=dict(ground_work), planning_counts=dict(planning_counts),
        model_rng_streams=len(raw),
        model_uniform_draws=planning_counts.get("model_uniform_draws", 0),
        censored_triplet=bool(outcomes["CUTOFF"]), seconds=perf_counter() - started)
    return games, raw, log
