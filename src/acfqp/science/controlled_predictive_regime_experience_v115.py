"""Natural 2048 episodes with a hidden, fixed tile-spawn regime for V115.

Only the tile-rank probability varies. Merges, rewards, terminal conditions,
empty-cell sampling, and observation records retain the V77 semantics.
"""
from __future__ import annotations

from collections import Counter
import random
from time import perf_counter
from typing import Callable

from acfqp.domains import standard_2048 as ground
from acfqp.science.controlled_predictive_lifelong_experience_v77 import _status


def _spawn(board: tuple[int, ...], rng: random.Random, work: Counter, p_four: float):
    empty = [cell for cell, rank in enumerate(board) if rank == 0]
    cell_draw, rank_draw = rng.random(), rng.random()
    work["environment_random_draws"] += 2
    cell = empty[int(cell_draw * len(empty))]
    rank = 1 if rank_draw < 1.0 - p_four else 2
    result = list(board)
    result[cell] = rank
    return tuple(result), cell, rank


def run_episode(
    seed: int,
    action_fn: Callable[[tuple[int, ...], int], str],
    p_four: float,
    max_steps: int = 2000,
) -> dict:
    """Play from two initial tiles, using a separate environment RNG.

    ``action_fn(board, step_index)`` returns one action name.  An illegal action
    fails the episode; it is never silently replaced.  Work counts cover this
    environment's calls, not computations performed inside ``action_fn``.
    """
    if not 0.0 <= p_four <= 1.0:
        raise ValueError("p_four must be between zero and one")
    if max_steps <= 0:
        raise ValueError("max_steps must be positive")
    started = perf_counter()
    rng, work = random.Random(seed), Counter()
    board = (0,) * 16
    initial_spawns = []
    for _ in range(2):
        board, cell, rank = _spawn(board, rng, work, p_four)
        initial_spawns.append(dict(cell=cell, rank=rank))
        work["initial_spawns"] += 1
    initial_board = board
    status = _status(board, work)
    steps, return_score = [], 0
    for index in range(max_steps):
        action = ground.Swipe2048Action(action_fn(board, index))
        work["ground_explicit_swipe_calls"] += 1
        work["ground_swipe_calls"] += 1
        afterstate, score, changed = ground.swipe_board_v1(board, action)
        if not changed:
            raise ValueError(f"illegal action {action.value} at step {index}")
        next_board, cell, rank = _spawn(afterstate, rng, work, p_four)
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
        seed=seed, initial_board=list(initial_board), initial_spawns=initial_spawns,
        final_board=list(board), status=status, return_score=return_score,
        steps_count=len(steps), steps=steps, work=dict(work),
        seconds=perf_counter() - started,
    )


def observed_rank(step: dict) -> int:
    """Infer the observed spawn from adjacent boards, without simulator metadata."""
    before, after = step["afterstate"], step["next_board"]
    if len(before) != 16 or len(after) != 16:
        raise ValueError("spawn observation requires two 16-cell boards")
    changes = [cell for cell in range(16) if before[cell] != after[cell]]
    if len(changes) != 1:
        raise ValueError("spawn observation requires exactly one changed cell")
    cell = changes[0]
    if before[cell] != 0 or after[cell] not in (1, 2):
        raise ValueError("spawn observation requires one empty cell becoming rank one or two")
    return int(after[cell])
