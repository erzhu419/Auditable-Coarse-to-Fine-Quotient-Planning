"""Continue a retained V78 sampled prefix without replaying its transitions."""
from __future__ import annotations

from collections import Counter
import random
from time import perf_counter
from typing import Callable

from acfqp.domains import standard_2048 as ground
from acfqp.science.controlled_predictive_lifelong_experience_v77 import _spawn, _status


def extend_episode(
    prefix: dict,
    action_fn: Callable[[tuple[int, ...], int], str],
    max_total_steps: int = 2000,
) -> dict:
    """Append sampled actions on the prefix's original environment RNG stream.

    The callback receives the absolute action index, starting at the retained
    prefix length.  Its own planning RNG is the caller's responsibility.  Work
    records only new suffix transitions; skipped RNG draws are reported
    separately.  A terminal or budget-exhausted prefix performs no new work.
    """
    if max_total_steps < 0:
        raise ValueError("max_total_steps must be nonnegative")
    started = perf_counter()
    board = tuple(prefix["final_board"])
    initial_board = board
    status = prefix["status"]
    prefix_steps = prefix["steps_count"]
    work, steps, return_score = Counter(), [], 0
    restoration_random_draws = 0
    resumed = status not in ("WON", "LOST") and prefix_steps < max_total_steps
    if resumed:
        rng = random.Random(prefix["seed"])
        restoration_random_draws = prefix["work"].get("environment_random_draws", 0)
        for _ in range(restoration_random_draws):
            rng.random()
        # CUTOFF is a budget label on the last observed ACTIVE state.
        status = "ACTIVE"
        for index in range(prefix_steps, max_total_steps):
            action = ground.Swipe2048Action(action_fn(board, index))
            work["ground_explicit_swipe_calls"] += 1
            work["ground_swipe_calls"] += 1
            afterstate, score, changed = ground.swipe_board_v1(board, action)
            if not changed:
                raise ValueError(f"illegal action {action.value} at step {index}")
            next_board, cell, rank = _spawn(afterstate, rng, work)
            work["sampled_transitions"] += 1
            status = _status(next_board, work)
            steps.append(dict(
                board=list(board), action=action.value, afterstate=list(afterstate),
                next_board=list(next_board), score=score, status=status,
                spawned_cell=cell, spawned_rank=rank,
            ))
            return_score += score
            board = next_board
            if status != "ACTIVE":
                break
    if status == "ACTIVE":
        status = "CUTOFF"
    seconds = perf_counter() - started
    suffix = dict(
        seed=prefix["seed"], initial_board=list(initial_board), initial_spawns=[],
        final_board=list(board), status=status, return_score=return_score,
        steps_count=len(steps), steps=steps, work=dict(work), seconds=seconds,
    )
    return dict(
        suffix=suffix, total_score=prefix["return_score"] + return_score,
        total_steps=prefix_steps + len(steps), status=status, resumed=resumed,
        restoration_random_draws=restoration_random_draws, seconds=seconds,
    )
