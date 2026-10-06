"""Bounded sampled continuations from an observed active 2048 board."""
from __future__ import annotations

from collections import Counter
import random
from time import perf_counter
from typing import Callable

from acfqp.domains import standard_2048 as ground
from acfqp.science.controlled_predictive_lifelong_experience_v77 import _spawn, _status


def rollout_from_board(
    board: tuple[int, ...],
    seed: int,
    action_fn: Callable[[tuple[int, ...], int], str],
    max_steps: int = 32,
) -> dict:
    """Sample one continuation, with no reset or initial spawn draws.

    Every executed action consumes exactly two environment random numbers, so
    equal seeds provide common random numbers even after first actions differ.
    The callback can force an initial action and then follow a fixed policy or
    replan.  Counts exclude computation inside that callback.  A nonterminal
    trajectory at the action budget is a cutoff, not an observed failure.
    """
    if max_steps <= 0:
        raise ValueError("max_steps must be positive")
    started = perf_counter()
    board = tuple(board)
    initial_board = board
    rng, work = random.Random(seed), Counter()
    status = _status(board, work)
    if status != "ACTIVE":
        raise ValueError("rollout must start from an ACTIVE board")
    steps, return_score = [], 0
    for index in range(max_steps):
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
    return dict(
        seed=seed, initial_board=list(initial_board), initial_spawns=[],
        final_board=list(board), status=status, return_score=return_score,
        steps_count=len(steps), steps=steps, work=dict(work),
        seconds=perf_counter() - started,
    )
